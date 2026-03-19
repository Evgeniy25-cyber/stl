#!/usr/bin/env python3

import logging
import sys
import os
import time

from flask import Flask, Response
from prometheus_client import CollectorRegistry, Gauge, generate_latest, CONTENT_TYPE_LATEST
from waitress import serve

from trex.common.stats.trex_stats import StatsBatch
from trex.stl.api import STLClient, STLError

# Конфигурационные параметры
TREX_SERVER = os.environ.get('TREX_SERVER', '127.0.0.1')
TREX_PORT = int(os.environ.get('TREX_PORT', 4501))
RETRY_BACKOFF = int(os.environ.get('RETRY_BACKOFF', 5))  # seconds

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация Flask-приложения
app = Flask(__name__)

class TRexMetricsCollector:
    def __init__(self, server, port):
        self.server = server
        self.port = port
        self.client = None
        self.connected = False
        self.extra_labels = {}
        self.server_stats = {}

    def connect(self):
        """Подключение к серверу TRex"""
        if self.client:
            try:
                self.client.disconnect()
            except Exception as e:
                logger.warning('Could not disconnect from TRex server: %s', e)

        self.client = STLClient(server=self.server, sync_port=self.port)
        try:
            self.client.connect()
            self.connected = True
            self.get_server_stats()
            logger.info("Connected to TRex server at %s:%d", self.server, self.port)
        except STLError as e:
            logger.error("Failed to connect to TRex: %s", e)
            self.connected = False

    def disconnect(self):
        """Отключение от сервера TRex"""
        if self.client:
            try:
                self.client.disconnect()
            except Exception as e:
                logger.warning('Could not disconnect from TRex server: %s', e)
        self.connected = False

    def get_server_stats(self):
        """Получение системных характеристик сервера"""
        try:
            server_info = self.client.get_server_system_info()
            self.server_stats = {
                'dp_core_count': server_info['dp_core_count'],
                'dp_core_count_per_port': server_info['dp_core_count_per_port'],
                'port_count': server_info['port_count'],
            }
            self.extra_labels = {
                'cpu_type': server_info['core_type'],
                'per_ports': [],
            }
            for port_id in range(self.server_stats['port_count']):
                self.extra_labels['per_ports'].append({
                    'nic': server_info['ports'][port_id]['description'],
                    'driver': server_info['ports'][port_id]['driver'],
                    'numa': server_info['ports'][port_id]['numa'],
                })
        except Exception as e:
            logger.error("Failed to get server stats: %s", e)

    def get_stats(self):
        """Сбор текущих статистических данных, включая латенцию"""
        stats = {}
        latency_stats = {}

        try:
            if not self.connected:
                self.connect()

            if self.connected:
                # Обновление глобальных статистик
                self.client.global_stats.update_sync(self.client.conn.rpc)
                stats['global'] = self.client.global_stats.to_dict()

                # Сбор статистики по портам
                port_stats = [
                    self.client.ports[port_id].get_port_stats()
                    for port_id in self.client.ports
                ]
                StatsBatch.update(port_stats, self.client.conn.rpc)
                for port_id, stat in enumerate(port_stats):
                    stats[port_id] = stat.to_dict()

                # Сбор статистики латенции (включая ICMP) - правильный метод
                try:
                    # Получаем статистику латенции через правильный API
                    # В разных версиях TRex API может отличаться
                    if hasattr(self.client, 'get_latency_stats'):
                        # Старый метод (если есть)
                        latency_stats = self.client.get_latency_stats()
                    elif hasattr(self.client, 'get_latency'):
                        # Новый метод
                        latency_stats = self.client.get_latency()
                    elif hasattr(self.client, 'get_latency_info'):
                        # Альтернативный метод
                        latency_stats = self.client.get_latency_info()
                    else:
                        # Пробуем получить через глобальные статистики
                        global_stats = self.client.global_stats.to_dict()
                        if 'latency' in global_stats:
                            latency_stats = global_stats['latency']
                        elif 'lat' in global_stats:
                            latency_stats = global_stats['lat']

                    if latency_stats:
                        stats['latency'] = latency_stats
                        logger.debug("Latency stats collected: %s", latency_stats)
                except Exception as e:
                    logger.debug("Failed to get latency stats: %s", e)
                    # Не логируем как ошибку, так как латенция может быть не настроена

        except Exception as e:
            logger.error("Failed to get stats from TRex server: %s", e)
            self.disconnect()

        return stats

    def ensure_connected(self):
        """Обеспечение стабильного подключения"""
        while not self.connected:
            try:
                self.connect()
                if self.connected:
                    return
            except STLError as e:
                logger.error(
                    "Connection error, retrying in %d sec: %s",
                    RETRY_BACKOFF, e
                )
                self.disconnect()
                time.sleep(RETRY_BACKOFF)

# Создание глобального экземпляра коллектора
trex_collector = TRexMetricsCollector(TREX_SERVER, TREX_PORT)

def collect_trex_stats():
    """Функция сбора метрик для Prometheus, включая ICMP"""
    registry = CollectorRegistry()
    seen_metrics = {
        'sys_heartbeat': Gauge(
            name="sys_heartbeat",
            documentation="Was connection to TRex successful",
            registry=registry
        ),
        'dp_core_count': Gauge(
            name="dp_core_count",
            documentation="Number of cores allocated to TRex",
            labelnames=['cpu_type'],
            registry=registry
        ),
        'dp_core_count_per_port': Gauge(
            name="dp_core_count_per_port",
            documentation="Number of cores allocated per dual-port",
            labelnames=['cpu_type'],
            registry=registry
        ),
    }

    try:
        trex_collector.ensure_connected()
        cpu_type = trex_collector.extra_labels.get('cpu_type', 'unknown')

        # Установка базовых метрик
        seen_metrics['dp_core_count'].labels(cpu_type=cpu_type).set(
            trex_collector.server_stats.get('dp_core_count', 0)
        )
        seen_metrics['dp_core_count_per_port'].labels(cpu_type=cpu_type).set(
            trex_collector.server_stats.get('dp_core_count_per_port', 0)
        )
        seen_metrics['sys_heartbeat'].set(1)

        stats = trex_collector.get_stats()

        # Обработка обычных статистик
        for key, stat in stats.items():
            if key == 'latency':
                continue  # Обрабатываем отдельно

            # Определение типа метрики и лейблов
            metric_type = 'global' if key == 'global' else 'per_port'
            port_label = str(key)

            nic = 'global'
            driver = 'global'
            numa = 'global'

            if isinstance(key, int) and key < len(trex_collector.extra_labels['per_ports']):
                nic = trex_collector.extra_labels['per_ports'][key]['nic']
                driver = trex_collector.extra_labels['per_ports'][key]['driver']
                numa = trex_collector.extra_labels['per_ports'][key]['numa']

            # Обработка всех полей статистики
            for metric_name, value in stat.items():
                # Фильтрация нечисловых значений
                if not isinstance(value, (int, float)):
                    continue

                # Создание метрики при первом обнаружении
                if metric_name not in seen_metrics:
                    g = Gauge(
                        name=metric_name,
                        documentation=f"TRex counter: {metric_name}",
                        labelnames=[
                            'port', 'metric_type', 'cpu_type',
                            'nic', 'driver', 'numa'
                        ],
                        registry=registry
                    )
                    seen_metrics[metric_name] = g

                # Установка значения метрики
                seen_metrics[metric_name].labels(
                    port=port_label,
                    metric_type=metric_type,
                    cpu_type=cpu_type,
                    nic=nic,
                    driver=driver,
                    numa=numa
                ).set(value)

        # Обработка статистики латенции (ICMP), если она есть
        if 'latency' in stats:
            latency_data = stats['latency']

            # Проверяем формат данных латенции
            if isinstance(latency_data, dict):
                # Обработка данных по портам
                for port_id, port_data in latency_data.items():
                    if not isinstance(port_id, int) and not port_id.isdigit():
                        continue

                    port_id_str = str(port_id)

                    # Получаем информацию о порте для лейблов
                    nic = 'unknown'
                    driver = 'unknown'
                    numa = 'unknown'

                    try:
                        port_num = int(port_id)
                        if port_num < len(trex_collector.extra_labels['per_ports']):
                            nic = trex_collector.extra_labels['per_ports'][port_num]['nic']
                            driver = trex_collector.extra_labels['per_ports'][port_num]['driver']
                            numa = trex_collector.extra_labels['per_ports'][port_num]['numa']
                    except (ValueError, TypeError):
                        pass

                    # Обработка всех полей латенции
                    if isinstance(port_data, dict):
                        for metric_name, value in port_data.items():
                            if not isinstance(value, (int, float)):
                                continue

                            # Создаем метрику для каждого поля латенции
                            metric_full_name = f"latency_{metric_name}"
                            if metric_full_name not in seen_metrics:
                                g = Gauge(
                                    name=metric_full_name,
                                    documentation=f"TRex latency {metric_name}",
                                    labelnames=[
                                        'port', 'cpu_type', 'nic', 'driver', 'numa'
                                    ],
                                    registry=registry
                                )
                                seen_metrics[metric_full_name] = g

                            seen_metrics[metric_full_name].labels(
                                port=port_id_str,
                                cpu_type=cpu_type,
                                nic=nic,
                                driver=driver,
                                numa=numa
                            ).set(value)

                    # Также проверяем наличие ICMP статистики в обычных статистиках порта
                    if port_id in stats and isinstance(stats[port_id], dict):
                        port_stats = stats[port_id]
                        # Ищем ICMP-related поля
                        icmp_fields = [k for k in port_stats.keys() if 'icmp' in k.lower()]
                        for icmp_field in icmp_fields:
                            value = port_stats[icmp_field]
                            if isinstance(value, (int, float)):
                                metric_full_name = f"icmp_{icmp_field}"
                                if metric_full_name not in seen_metrics:
                                    g = Gauge(
                                        name=metric_full_name,
                                        documentation=f"TRex ICMP {icmp_field}",
                                        labelnames=[
                                            'port', 'cpu_type', 'nic', 'driver', 'numa'
                                        ],
                                        registry=registry
                                    )
                                    seen_metrics[metric_full_name] = g

                                seen_metrics[metric_full_name].labels(
                                    port=port_id_str,
                                    cpu_type=cpu_type,
                                    nic=nic,
                                    driver=driver,
                                    numa=numa
                                ).set(value)

    except Exception as e:
        logger.error("Failed to collect metrics: %s", e)
        seen_metrics['sys_heartbeat'].set(0)

    return registry

@app.route('/metrics')
def metrics():
    registry = collect_trex_stats()
    return Response(generate_latest(registry), mimetype=CONTENT_TYPE_LATEST)

@app.route('/')
def index():
    """Корневой эндпоинт с информацией"""
    return """
    <html>
        <head><title>TRex Prometheus Exporter</title></head>
        <body>
            <h1>TRex Prometheus Exporter</h1>
            <p>Экспортер метрик TRex для Prometheus</p>
            <ul>
                <li><a href="/metrics">Metrics</a> - метрики в формате Prometheus</li>
            </ul>
            <p>Подключение к TRex серверу: {server}:{port}</p>
            <p>Статус: <span style="color: green;">✓ Работает</span></p>
        </body>
    </html>
    """.format(server=TREX_SERVER, port=TREX_PORT)

if __name__ == '__main__':
    logger.info("Starting TRex Prometheus Exporter")
    logger.info("TRex Server: %s:%d", TREX_SERVER, TREX_PORT)
    logger.info("Exporter Port: 9362")

    # Инициализация подключения при старте
    try:
        trex_collector.connect()
    except Exception as e:
        logger.warning("Initial connection failed: %s", e)

    serve(app, host='0.0.0.0', port=9362)






































