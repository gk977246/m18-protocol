import struct
import time
from machine import UART, Pin
import utime

# MicroPython-safe bit reversal lookup (avoids [::-1] slice limitation)
_NIBBLE_REV = (0x0, 0x8, 0x4, 0xC, 0x2, 0xA, 0x6, 0xE, 0x1, 0x9, 0x5, 0xD, 0x3, 0xB, 0x7, 0xF)

class M18:
    def __init__(self, tx_pin=22, rx_pin=27, baudrate=4800, debug=True):
        self.baudrate = baudrate
        self.tx_pin = tx_pin
        self.rx_pin = rx_pin
        self.debug = debug
        self.acc = 4
        
        # Start as GPIO to enforce IDLE state immediately
        self.line = Pin(tx_pin, Pin.OUT)
        self.line.value(0)  # IDLE = HIGH (prevents charge count)
        time.sleep_ms(300)
        
    # ──────────────────────────────────────────────────────────────────
    # MICROPYTHON-SAFE BIT REVERSAL
    # ──────────────────────────────────────────────────────────────────
    @staticmethod
    def _rev_byte(b):
        """Reverse 8 bits using 4-bit lookup table"""
        return (_NIBBLE_REV[b & 0x0F] << 4) | _NIBBLE_REV[b >> 4]

    @staticmethod
    def _rev_buf(data):
        """Apply bit reversal to entire buffer (MP-safe list comp)"""
        return bytearray([M18._rev_byte(b) for b in data])

    @staticmethod
    def _parse_cell_voltages(raw_bytes):
        """Parse 10 bytes → list of 5 cell voltages in mV"""
        if not raw_bytes or len(raw_bytes) < 10:
            return [0] * 5
        return [int.from_bytes(raw_bytes[i:i+2], 'big') for i in range(0, 10, 2)]

    def _safe_read_register(self, msb, lsb, length, header_offset=3):
        """Read register with error handling, return payload only"""
        try:
            resp = self.cmd(msb, lsb, length)
            # Response format: [0x81, ??, ??, <payload>, <cksum>]
            if resp and len(resp) >= header_offset + length and resp[0] == 0x81:
                return resp[header_offset:header_offset + length]
        except:
            pass
        return None    
    # ──────────────────────────────────────────────────────────────────
    # SAFE STATE SWITCHING
    # ──────────────────────────────────────────────────────────────────
    def _set_idle(self):
        """IDLE STATE: Pin17 HIGH (0)"""
        try:
            self.uart.deinit()
        except:
            pass
        self.line.init(mode=Pin.OUT)
        self.line.value(0)
        time.sleep_ms(5)
        self._dbg("STATE", "IDLE (Pin17= 0)")
        
    def _set_active(self):
        """ACTIVE STATE: Pin17  (0) → UART takes over"""
        try:
            self.uart.deinit()
        except:
            pass
            
        # Pull LOW briefly for break condition
        self.line.init(mode=Pin.OUT)
        self.line.value(0)
        time.sleep_ms(300)
        
        # Release GPIO so UART peripheral can claim it
        self.line.init(mode=Pin.IN, pull=None)
        time.sleep_ms(300)
        
        # Initialize UART
        self.uart = UART(2, baudrate=self.baudrate, bits=8, parity=None, 
                         stop=2, tx=self.tx_pin, rx=self.rx_pin, timeout=500)
        self._dbg("STATE", "ACTIVE (Pin17= → UART)")
        
    # ──────────────────────────────────────────────────────────────────
    # SAFE DEBUG PRINTING (MicroPython compatible)
    # ──────────────────────────────────────────────────────────────────
    def _dbg(self, label, data):
        if not self.debug:
            return
        if isinstance(data, (bytes, bytearray)):
            hex_str = " ".join("%02X" % b for b in data)
        else:
            hex_str = str(data)
        print("[%s] %s" % (label, hex_str))
        
    # ──────────────────────────────────────────────────────────────────
    # PROTOCOL CORE
    # ──────────────────────────────────────────────────────────────────
    def _send(self, logical_data):
        wire_data = self._rev_buf(logical_data)
        self._dbg("TX-LOG", logical_data)
        self._dbg("TX-WIRE", wire_data)
        self.uart.write(wire_data)
        # 4800 baud ≈ 2.08ms/byte. Wait safely for buffer flush.
        time.sleep_ms(max(15, len(wire_data) * 3))
        
    def _read(self, n, timeout_ms=300):
        buf = bytearray()
        start = time.ticks_ms()
        while len(buf) < n:
            chunk = self.uart.read(n - len(buf))
            if chunk:
                buf.extend(chunk)
            if time.ticks_diff(time.ticks_ms(), start) > timeout_ms:
                break
            time.sleep_ms(1)
        self._dbg("RX", buf if buf else None)
        #return buf
        if not buf:
            self._dbg("RX", "TIMEOUT")
            return bytearray()
            
        logical = self._rev_buf(buf)
        self._dbg("RX-WIRE", buf)
        self._dbg("RX-LOG", logical)
        return logical
        
    def reset(self):
        self.acc = 4
        #self._set_idle()
        #time.sleep_ms(290)
        self._set_active()
        #time.sleep_ms(290)
        
        self._send(b'\xAA')
        time.sleep_ms(190)
        resp = self._read(2)
        return len(resp) == 1 and resp[0] == 0xAA
        
    def cmd(self, addr_msb, addr_lsb, length, resp_len=None):
        if resp_len is None:
            resp_len = length + 5
        payload = struct.pack('>BBBBBB', 0x01, 0x04, 0x03, addr_msb, addr_lsb, length)
        cksum = struct.pack('>H', sum(payload) & 0xFFFF)
        self._send(payload + cksum)
        return self._read(resp_len)
        
    def read_health(self):
        print("\n=== READING HEALTH REGISTERS ===")
        self.reset()
        #self._set_active()
        
        targets = [(0x00, 0x00, 2), (0x00, 0x04, 5), (0x90, 0x1E, 2), (0x40, 0x0A, 10)]
        for msb, lsb, length in targets:
            addr = (msb << 8) | lsb
            print("\n--- Reading 0x%04X ---" % addr)
            resp = self.cmd(msb, lsb, length)
            if len(resp) >= 4 and resp[0] == 0x81:
                data = resp[3:3+length]
                print(" OK: %s" % " ".join("%02X" % b for b in data))
            else:
                print(" FAIL: %s" % (resp.hex() if resp else "TIMEOUT"))
                
        self._set_idle()
        print("\n=== BACK TO IDLE (Pin17=HIGH) ===\n")

    def get_health_lcd(self):
        """Fetch health data with targeted bucket range (10-210A)"""
        self.reset()
        utime.sleep_ms(50)
    
        # Core registers
        cells_raw = self._safe_read_register(0x40, 0x0A, 10)
        days_raw = self._safe_read_register(0x90, 0x10, 2)  # Days since first charge
        discharge_raw = self._safe_read_register(0x90, 0x12, 4)
        charge_total_raw = self._safe_read_register(0x90, 0x1A, 4)
        redlink_raw = self._safe_read_register(0x90, 0x20, 2)
        lowv_raw = self._safe_read_register(0x90, 0x2E, 2)
    
        # ─── Parse Core Values ─────────────────────────────────────────
        cells = [int.from_bytes(cells_raw[i:i+2], 'big') for i in range(0, 10, 2)] if cells_raw and len(cells_raw)>=10 else [0]*5
        days_since_first = int.from_bytes(days_raw, 'big') if days_raw and len(days_raw)>=2 else 0
        years = (int.from_bytes(days_raw, 'big') / 365.0) if days_raw and len(days_raw)>=2 else 0
        total_ah = (int.from_bytes(discharge_raw, 'big') / 3600.0) if discharge_raw and len(discharge_raw)>=4 else 0
        charge_total = int.from_bytes(charge_total_raw, 'big') if charge_total_raw and len(charge_total_raw)>=4 else 0
        redlink_count = int.from_bytes(redlink_raw, 'big') if redlink_raw and len(redlink_raw)>=2 else 0
        lowv_charge_count = int.from_bytes(lowv_raw, 'big') if lowv_raw and len(lowv_raw)>=2 else 0
    
        # ─── BUCKETS 0x903A to 0x9060 (10-20A to 200-210A) ───────────
        buckets = []
        bucket_addrs = range(0x903A, 0x9060, 2)  # 20 registers
        for addr in bucket_addrs:
            msb = (addr >> 8) & 0xFF
            lsb = addr & 0xFF
            raw = self._safe_read_register(msb, lsb, 2)
            val = int.from_bytes(raw, 'big') if raw and len(raw)>=2 else 0
            buckets.append(val)
        
        self._set_idle()
    
        # Calculate percentages
        total_bucket_sec = sum(buckets)
        bucket_pct = [round((s / total_bucket_sec) * 100) if total_bucket_sec > 0 else 0 for s in buckets]
    
        return {
            'cells': cells,
            'total_v': sum(cells) / 1000.0,
            'imbalance': max(cells) - min(cells),
            'days_since_first': days_since_first,
            'years': years,
            'total_ah': total_ah,
            'charge_total': charge_total,
            'redlink_count': redlink_count,
            'lowv_charge_count': lowv_charge_count,
            'buckets': buckets,          # Raw seconds [10-20A, ... 200-210A]
            'bucket_pct': bucket_pct,    # Percentages
            'bucket_total_sec': total_bucket_sec
        }

#m = M18(tx_pin=17, rx_pin=16, debug=True)
#m.read_health()        
#mfg_raw = m._safe_read_register(0x90, 0x10, 2)
#print("Raw Date Hex:", mfg_raw.hex() if mfg_raw else "None")

#health = m.get_health_lcd()

# Debug output
#print(f"✅ Pack: {health['total_v']:.2f}V | Imbalance: {health['imbalance']}mV")
#print(f"✅ Cells: {health['cells']} mV")
#print(f"✅ Days: {health['days_since_first']}")
#print(f"✅ Total Ah: {health['total_ah']:.2f} | Cycles: {health['charge_total']}")
#print(f"✅ Redlink Count: {health['redlink_count']} | LowV Starts: {health['lowv_charge_count']}")
#print(f"✅ Top buckets: {[(i+1)*10 for i, v in enumerate(health['buckets'][:5]) if v > 0]}")
#print(f"✅ buckets %: {health['bucket_pct']} %")