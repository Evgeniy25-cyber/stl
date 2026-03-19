prometeus
apt install chrony
systemctl enable chrony
systemctl start chrony

tar -zxf prometheus-3.9.1.linux-amd64.tar.gz
cd prometheus-3.9.1.linux-amd64
sudo mkdir -p /opt/prometheus/
sudo mv prometheus prometheus.yml promtool /opt/prometheus/
sudo nano /etc/systemd/system/prometheus.service
---------------------------------------------------------
[Unit]
Description=Prometheus Monitoring
Wants=network-online.target
After=network-online.target

[Service]
User=prometheus
Group=prometheus
ExecStart=/opt/prometheus/prometheus \
  --config.file=/opt/prometheus/prometheus.yml \
  --storage.tsdb.path=/opt/prometheus/data \
  --web.listen-address=0.0.0.0:9090
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
===================================================================
sudo systemctl daemon-reload
sudo systemctl enable --now prometheus
sudo systemctl status prometheus
=====================================================================================================
sudo chown -R prometheus:prometheus /opt/prometheus/
------------------------------------------------------------


sudo mv prometheus prometheus.yml promtool /opt/prometheus/
=====================================================
sudo nano /opt/prometheus/prometheus.yml
==================================================
# my global config
global:
  scrape_interval: 15s
  evaluation_interval: 15s

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          # - alertmanager:9093


rule_files:
  # - "first_rules.yml"
  # - "second_rules.yml"

scrape_configs:
  - job_name: "prometheus"
    static_configs:
      - targets: ["localhost:9090"]
        labels:
          app: "prometheus"

  - job_name: "ciscotrex-exporter"
    static_configs:
      - targets: ["10.20.51.149:9362"]
=====================================================================
sudo nano /opt/prometheus/prometheus.yml
==================================================
# my global config
global:
  scrape_interval: 15s
  evaluation_interval: 15s

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          # - alertmanager:9093


rule_files:
  # - "first_rules.yml"
  # - "second_rules.yml"

scrape_configs:
  - job_name: "prometheus"
    static_configs:
      - targets: ["localhost:9090"]
        labels:
          app: "prometheus"

  - job_name: "ciscotrex-exporter"
    static_configs:
      - targets: ["10.20.51.149:9362"]



=====================================================================

curl http://localhost:9362/metrics
python3 -m venv /root/venv
source /root/venv/bin/activate
source /root/venv/bin/activate
pip install prometheus-client requests
Проверьте запуск вручную:

bash
/root/venv/bin/python /opt/ciscotrex_exporter/main.py --web.listen-address=0.0.0.0:9362

================================================================================
Обычно эта папка находится в дистрибутиве TRex. Проверьте возможные пути:

bash
ls /opt/trex/  # стандартный путь установки TRex
ls /usr/local/trex/
ls ~/trex/
export TREX_EXT_LIBS=/opt/trex/external_libs
echo $TREX_EXT_LIBS
export TREX_EXT_LIBS=/opt/v3.08/external_libs
Шаг 2. Переместите venv в общедоступное место (рекомендуется)
systemd не любит работать с /root/. Перенесите venv в /opt/ или /usr/local/:
ExecStart=/opt/venv/trex_exporter_venv/bin/python /opt/ciscotrex_exporter/main.py --web.listen-address=":9362"
bash
sudo mv /root/venv /opt/ciscotrex_venv
root@cisco-trex:~# cd /opt/ciscotrex_venv
root@cisco-trex:/opt/ciscotrex_venv# source bin/activate
============================================================================
sudo apt update
sudo apt install python3-venv  # общий пакет для текущей версии Python
Шаг 2. Пересоздайте виртуальное окружение
После установки пакета:

bash
# Удалите сломанное окружение (если есть)
sudo rm -rf /opt/ciscotrex_venv

# Создайте новое
python3 -m venv /opt/ciscotrex_venv
Проверка:
Должны появиться файлы:

/opt/ciscotrex_venv/bin/activate

/opt/ciscotrex_venv/bin/python3

Шаг 3. Активируйте окружение
bash
source /opt/ciscotrex_venv/bin/activate  ======== =======
Обновите путь в /etc/systemd/system/ciscotrex_exporter.service:
=============================================================
sudo nano /etc/systemd/system/ciscotrex_exporter.service
-----------------------------------------------------------
[Unit]
Description=Cisco-TRex Prometheus exporter
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=prometheus
Group=prometheus
WorkingDirectory=/opt/ciscotrex_exporter
Environment="TREX_EXT_LIBS=/opt/trex/external_libs"
Environment="TREX_HOST=localhost"
Environment="TREX_ZMQ_PORT=4501"
ExecStart=/opt/ciscotrex_venv/bin/python /opt/ciscotrex_exporter/main.py --web.listen-address=0.0.0.0:9362
ExecStart=/opt/ciscotrex_venv/bin/python /opt/ciscotrex_exporter/main.py --web.listen-address=0.0.0.0:9362
Restart=always
RestartSec=5


[Install]
WantedBy=multi-user.target


------------------------------------------------------------------------
sudo systemctl daemon-reexec
sudo systemctl daemon-reload
sudo systemctl restart ciscotrex_exporter
sudo systemctl status ciscotrex_exporter
=======================================================================
sudo journalctl -u ciscotrex_exporter -n 50
chmod -R 755 /opt/trex/external_libs  # замените путь на ваш
chown -R root:root /opt/--trex---/external_libs
source /root/venv/bin/activate
pip list
============================================================================
curl http://10.20.51.149:9362/metrics
===================================================================
====================================================================
2. Исправление ModuleNotFoundError: No module named ‘distutils’
Причина:
Модуль distutils входит в пакет setuptools, который не установлен в вашем виртуальном окружении.

Решение:
Установите setuptools в активированном venv:

bash
pip install --break-system-packages setuptools
Проверка:
Убедитесь, что модуль доступен:

bash
python -c "from distutils.util import strtobool; print('OK')"
Если вывод:

OK
— проблема решена.

3. Дополнительные проверки
Убедитесь, что venv активен
Приглашение должно содержать (ciscotrex_venv).
Если нет — активируйте:

bash
source /opt/ciscotrex_venv/bin/activate
======================================================================================
curl http://localhost:9362/metrics
python3 -m venv /root/venv
source /root/venv/bin/activate
source /root/venv/bin/activate
pip install prometheus-client requests
Проверьте запуск вручную:

bash
/root/venv/bin/python /opt/ciscotrex_exporter/main.py --web.listen-address=0.0.0.0:9362

================================================================================
Обычно эта папка находится в дистрибутиве TRex. Проверьте возможные пути:

bash
ls /opt/trex/  # стандартный путь установки TRex
ls /usr/local/trex/
ls ~/trex/
export TREX_EXT_LIBS=/opt/trex/external_libs
echo $TREX_EXT_LIBS
export TREX_EXT_LIBS=/opt/v3.08/external_libs
Шаг 2. Переместите venv в общедоступное место (рекомендуется)
systemd не любит работать с /root/. Перенесите venv в /opt/ или /usr/local/:
ExecStart=/opt/venv/trex_exporter_venv/bin/python /opt/ciscotrex_exporter/main.py --web.listen-address=":9362"
bash
sudo mv /root/venv /opt/ciscotrex_venv
root@cisco-trex:~# cd /opt/ciscotrex_venv
root@cisco-trex:/opt/ciscotrex_venv# source bin/activate
============================================================================
sudo apt update
sudo apt install python3-venv  # общий пакет для текущей версии Python
Шаг 2. Пересоздайте виртуальное окружение
После установки пакета:

bash
# Удалите сломанное окружение (если есть)
sudo rm -rf /opt/ciscotrex_venv

# Создайте новое
python3 -m venv /opt/ciscotrex_venv
Проверка:
Должны появиться файлы:

/opt/ciscotrex_venv/bin/activate

/opt/ciscotrex_venv/bin/python3

Шаг 3. Активируйте окружение
bash
source /opt/ciscotrex_venv/bin/activate  ======== =======
Обновите путь в /etc/systemd/system/ciscotrex_exporter.service:
=============================================================
sudo nano /etc/systemd/system/ciscotrex_exporter.service
-----------------------------------------------------------
[Unit]
Description=Cisco-TRex Prometheus exporter
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=prometheus
Group=prometheus
WorkingDirectory=/opt/ciscotrex_exporter
Environment="TREX_EXT_LIBS=/opt/v3.07/external_libs"
Environment="TREX_HOST=localhost"
Environment="TREX_ZMQ_PORT=4501"
ExecStart=/opt/venv/trex_exporter_venv/bin/python /opt/ciscotrex_exporter/main.py --web-listen-address=:9362



Restart=always
RestartSec=5


[Install]
WantedBy=multi-user.target



------------------------------------------------------------------------
sudo systemctl daemon-reexec
sudo systemctl daemon-reload
sudo systemctl restart ciscotrex_exporter
sudo systemctl status ciscotrex_exporter
=======================================================================
sudo journalctl -u ciscotrex_exporter -n 50
chmod -R 755 /opt/trex/external_libs  # замените путь на ваш
chown -R root:root /opt/--trex---/external_libs
source /root/venv/bin/activate
pip list
============================================================================
проверка метрик осуществиться данной командой 
curl http://10.20.51.149:9362/metrics
===================================================================
====================================================================
2. Исправление ModuleNotFoundError: No module named ‘distutils’
Причина:
Модуль distutils входит в пакет setuptools, который не установлен в вашем виртуальном окружении.

Решение:
Установите setuptools в активированном venv:

bash
pip install --break-system-packages setuptools
Проверка:
Убедитесь, что модуль доступен:

bash
python -c "from distutils.util import strtobool; print('OK')"
Если вывод:

OK
— проблема решена.

3. Дополнительные проверки
Убедитесь, что venv активен
Приглашение должно содержать (ciscotrex_venv).
Если нет — активируйте:

bash
source /opt/ciscotrex_venv/bin/activate



==================================================
sudo lsof -i :9362
sudo ufw allow 4500/tcp
sudo ufw disable
sudo -u prometheus timeout 2 bash -c "cat < /dev/tcp/10.20.51.10/4500" && echo "TCP 4500 open" || echo "TCP 4500 closed/blocked"
TCP 4500 closed/blocked
ps -ef | grep '[t]-rex.*zmq'
sudo lsof -i :4500
 sudo ./t-rex-64 -i --emu-zmq-tcp 0.0.0.0:4500 --no-ofed-check --no-scapy-server
 ./t-rex-64 -i --emu-zmq-tcp 10.20.51.149:4500 --no-ofed-check --no-scapy-server
 nano /etc/prometheus/prometheus.yml
journalctl -u prometheus.service -b
==============================================================================================
echo 4 > /sys/class/net/ens22f0np0/device/sriov_numvfs
echo 4 > /sys/class/net/ens22f1np1/device/sriov_numvfs

echo 1 > /sys/class/net/ens22f0np0/device/sriov_numvfs
echo 1 > /sys/class/net/ens22f1np1/device/sriov_numvfs


  
