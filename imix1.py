from trex_stl_lib.api import *
import argparse
import os

class STLImix(object):

    def __init__(self):
        # Р’Р°С€Рё IPвЂ‘РґРёР°РїР°Р·РѕРЅС‹ РґР»СЏ РєР°Р¶РґРѕРіРѕ РїРѕСЂС‚Р°
        self.ip_ranges = {
            0: {
                'src': {'start': "16.0.0.1",  'end': "16.0.255.254"},
                'dst': {'start': "48.0.0.1",  'end': "48.0.255.254"}
            },
            1: {
                'src': {'start': "48.0.0.1", 'end': "48.0.255.254"},
                'dst': {'start': "16.0.0.1", 'end': "16.0.255.254"}
            },
            2: {
                'src': {'start': "17.0.0.1", 'end': "17.0.255.254"},
                'dst': {'start': "49.0.0.1", 'end': "49.0.255.254"}
            },
            3: {
                'src': {'start': "49.0.0.1", 'end': "49.0.255.254"},
                'dst': {'start': "17.0.0.1", 'end': "17.0.255.254"}
            }
        }

        # IMIXвЂ‘С‚Р°Р±Р»РёС†Р°: СЂР°Р·РјРµСЂ РїР°РєРµС‚Р°, PPS, РјРµР¶РїР°РєРµС‚РЅС‹Р№ РёРЅС‚РµСЂРІР°Р» (ISG)
        self.imix_table = [
            {'size': 60,   'pps': 28,  'isg': 0.0},
            {'size': 590,  'pps': 16,  'isg': 0.1},
            {'size': 1514, 'pps': 4,   'isg': 0.2}
        ]

        # MACвЂ‘Р°РґСЂРµСЃР° Рё VLAN РґР»СЏ РєР°Р¶РґРѕРіРѕ РїРѕСЂС‚Р° (Р·Р°РјРµРЅРёС‚Рµ РЅР° СЂРµР°Р»СЊРЅС‹Рµ РёР· portattr)
        self.macs = {
            0: {'src': "f6:c8:27:bf:6f:52", 'dst': "90:54:b7:79:a4:83"},
            1: {'src': "02:88:6c:36:b6:10", 'dst': "90:54:b7:79:ac:83"},
            2: {'src': "66:a0:57:d7:34:74", 'dst': "90:54:b7:79:a4:83"},  # Р·Р°РјРµРЅРёС‚Рµ РЅР° СЂРµР°Р»СЊРЅС‹Рµ
            3: {'src': "3e:f6:6e:08:11:88", 'dst': "90:54:b7:79:ac:83"}   # Р·Р°РјРµРЅРёС‚Рµ РЅР° СЂРµР°Р»СЊРЅС‹Рµ
        }
        self.vlan_ids = {0: 101, 1: 102, 2: 103, 3: 104}

    def create_stream(self, size, pps, isg, vm, src_mac, dst_mac, vlan_id):
        # РЎРѕР·РґР°С‘Рј Р±Р°Р·РѕРІС‹Р№ РїР°РєРµС‚ СЃ MAC Рё VLAN
        base_pkt = Ether(src=src_mac, dst=dst_mac)
        if vlan_id:
            base_pkt /= Dot1Q(vlan=vlan_id)  # Р”РѕР±Р°РІР»СЏРµРј VLANвЂ‘С‚РµРі
        base_pkt /= IP()/UDP()

        # Р”РѕРїРѕР»РЅСЏРµРј РїР°РєРµС‚РѕРј РґРѕ РЅСѓР¶РЅРѕРіРѕ СЂР°Р·РјРµСЂР°
        pad = max(0, size - len(base_pkt)) * 'x'
        pkt = STLPktBuilder(pkt=base_pkt/pad, vm=vm)


        return STLStream(
            isg=isg,
            packet=pkt,
            mode=STLTXCont(pps=pps)
        )

    def get_streams(self, direction=0, tunables="", **kwargs):
        # РџР°СЂСЃРёРј Р°СЂРіСѓРјРµРЅС‚С‹ (РµСЃР»Рё РЅСѓР¶РЅС‹ РґРѕРїРѕР»РЅРёС‚РµР»СЊРЅС‹Рµ РЅР°СЃС‚СЂРѕР№РєРё)
        parser = argparse.ArgumentParser(
            description='Argparser for {}'.format(os.path.basename(__file__)),
            formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )
        args, unknown = parser.parse_known_args(tunables)
        if unknown:
            raise Exception('Unrecognized arguments: {}'.format(unknown))


        port_id = kwargs.get('port_id', 0)

        # Р’С‹Р±РёСЂР°РµРј IPвЂ‘РґРёР°РїР°Р·РѕРЅС‹ РґР»СЏ РїРѕСЂС‚Р°
        if direction == 0:
            src = self.ip_ranges[port_id]['src']
            dst = self.ip_ranges[port_id]['dst']
        else:
            src = self.ip_ranges[port_id]['dst']
            dst = self.ip_ranges[port_id]['src']

        # VMвЂ‘С€Р°Р±Р»РѕРЅ РґР»СЏ РіРµРЅРµСЂР°С†РёРё IP
        vm = STLVM()
        vm.var(name="src_ip", min_value=src['start'], max_value=src['end'], size=4, op="inc")
        vm.var(name="dst_ip", min_value=dst['start'], max_value=dst['end'], size=4, op="inc")
        vm.write(fv_name="src_ip", pkt_offset="IP.src")
        vm.write(fv_name="dst_ip", pkt_offset="IP.dst")
        vm.fix_chksum()  # РСЃРїСЂР°РІР»СЏРµРј checksum

        # РџРѕР»СѓС‡Р°РµРј MAC Рё VLAN РґР»СЏ РїРѕСЂС‚Р°
        src_mac = self.macs[port_id]['src']
        dst_mac = self.macs[port_id]['dst']
        vlan_id = self.vlan_ids[port_id]

        # РЎРѕР·РґР°С‘Рј РїРѕС‚РѕРєРё РґР»СЏ IMIX
        return [
            self.create_stream(x['size'], x['pps'], x['isg'], vm, src_mac, dst_mac, vlan_id)
            for x in self.imix_table
        ]

# Р¤СѓРЅРєС†РёСЏ РґР»СЏ РґРёРЅР°РјРёС‡РµСЃРєРѕР№ Р·Р°РіСЂСѓР·РєРё РїСЂРѕС„РёР»СЏ РІ TRex
def register():
    return STLImix()
