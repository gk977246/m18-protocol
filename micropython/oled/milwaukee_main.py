from m18 import M18
from machine import Pin, I2C
#import machine
import time

i2c = I2C(0, scl=Pin(9), sda=Pin(8), freq=400000)
# ─── SH1106 Driver Import (choose one) ──────────────────────────────
# Option A: Dedicated SH1106 library (recommended)
# Download: https://github.com/robert-hh/SH1106
try:
    from sh1106 import SH1106_I2C
    USE_SH1106 = True
except ImportError:
    # Option B: Fallback using SSD1306 driver (works with SH1106)
    # Download: https://github.com/micropython/micropython-lib/tree/master/micropython/drivers/display/ssd1306
    from ssd1306 import SSD1306_I2C
    USE_SH1106 = False

# ─── Helper: Monochrome Bar Chart ───────────────────────────────────
def draw_bar_mono(oled, x, y, w, h, value, max_val):
    """Draw a simple monochrome progress bar"""
    if max_val > 0 and w > 0:
        fill_w = min(w, max(0, int((value / max_val) * w)))
        if fill_w > 0:
            oled.fill_rect(x, y, fill_w, h, 1)
    oled.rect(x, y, w, h, 1)  # Border

class App:
    def __init__(self):
        self.screen_idx = 0
        self.health = None
        self.last_button_time = 0
        self.debounce_ms = 300
        
        # ─── Hardware Init ──────────────────────────────────────────
        # I2C for SH1106 (ADJUST PINS FOR YOUR BOARD!)
        # ESP32 example: SDA=21, SCL=22 | RP2040: SDA=0, SCL=1
        #self.i2c = I2C(0, scl=Pin(9), sda=Pin(8), freq=400000)
        
        if USE_SH1106:
            self.oled = SH1106_I2C(128, 64, i2c, addr=0x3c, rotate=180)
        else:
            self.oled = SSD1306_I2C(128, 64, i2c, addr=0x3c)
        
        self.oled.init_display()
        self.oled.contrast(255)
        self.oled.fill(0)
        
        # Button on Pin 0 (active-low with internal pull-up)
        self.btn = Pin(0, Pin.IN, Pin.PULL_UP)
        
        # M18 Protocol
        self.m18 = M18(tx_pin=20, rx_pin=21, debug=False)
        
        # Initial display
        self.draw_ui_frame()
        self.update_data()
        
    def read_button(self):
        """Debounced button read. Returns True on press."""
        if self.btn.value() == 0:  # Active-low pressed
            now = time.ticks_ms()
            if time.ticks_diff(now, self.last_button_time) > self.debounce_ms:
                self.last_button_time = now
                # Wait for release to prevent repeat
                while self.btn.value() == 0:
                    time.sleep_ms(10)
                return True
        return False

    def handle_input(self):
        """Handle button: cycle through 3 screens"""
        if self.read_button():
            self.screen_idx = (self.screen_idx + 1) % 3
            self.draw_ui_frame()
            self.update_display()

    def draw_ui_frame(self):
        """Draw header and page indicator"""
        self.oled.fill(0)  # Clear buffer
        titles = ["CELLS", "OVERVIEW", "USAGE"]
        #self.oled.text(f"{titles[self.screen_idx]} [{self.screen_idx+1}/3]", 0, 0, 1)
        self.oled.text(f"{titles[self.screen_idx]}", 0, 0, 1)
        self.oled.hline(0, 9, 128, 1)  # Separator

    def update_data(self):
        """Fetch and display M18 data"""
        self.oled.text("Reading...", 60, 0, 1)
        self.oled.show()
        try:
            self.health = self.m18.get_health_lcd()
            self.update_display()
        except Exception as e:
            print("Error:", e)
            self.oled.fill(0)
            self.oled.text("ERROR", 0, 0, 1)
            self.oled.text(str(e)[:16], 0, 12, 1)
            self.oled.show()

    def update_display(self):
        """Render active screen"""
        if not self.health:
            return
        h = self.health
        if self.screen_idx == 0:
            self.draw_cells(h)
        elif self.screen_idx == 1:
            self.draw_overview(h)
        elif self.screen_idx == 2:
            self.draw_usage(h)
        self.oled.show()

    def draw_overview(self, h):
        """Screen 1: Key stats"""
        y = 16
        self.oled.text(f"{h['total_v']:.2f}V", 80, 0, 1);
        self.oled.text(f"Diff:{h['imbalance']}mV", 0, y, 1); y += 10
        self.oled.text(f"Ah  :{h['total_ah']:.1f}Ah", 0, y, 1); y += 10
        self.oled.text(f"D/Y :{h['days_since_first']}/{h['years']:.1f}", 0, y, 1); y += 10
        self.oled.text(f"Chg :{h['redlink_count']} {h['charge_total']}Total", 0, y, 1); y += 10
        self.oled.text(f"LowV:{h['lowv_charge_count']}", 0, y, 1)

    def draw_cells(self, h):
        """Screen 0: Cell voltages (first 5 due to space)"""
        cells = h['cells']
        y = 16
        for i in range(min(5, len(cells))):
            v = cells[i]
            status = "!" if v < 3000 else ""
            self.oled.text(f"C{i+1}:{v}{status}mV", 0, y, 1)
            y += 10
        if len(cells) > 5:
            self.oled.text(f"+{len(cells)-5} more", 0, 54, 1)

    def draw_usage(self, h):
        """Screen 2: Top discharge buckets"""
        buckets = h['buckets']
        pcts = h['bucket_pct']
        total_min = h['bucket_total_sec'] // 60
        
        y = 11
        self.oled.text(f"Total:{total_min}min", 0, y, 1); y += 9
        
        # Show top 3 current ranges by usage
        indexed = sorted(enumerate(zip(buckets, pcts)), 
                        key=lambda x: x[1][0], reverse=True)
        
        for i in range(min(5, len(indexed))):
            idx, (sec, pct) = indexed[i]
            label = f"{(idx+1)*10}-{(idx+2)*10}A"
            self.oled.text(f"{label}:{pct:.0f}%", 0, y, 1)
            # Mini bar
            #draw_bar_mono(self.oled, 70, y-1, int(pct * 0.5), 7, pct, 100)
            y += 9

# ─── Main Loop ──────────────────────────────────────────────────────
#try:
app = App()
while True:
    app.handle_input()
    time.sleep_ms(5)  # CPU idle
#except KeyboardInterrupt:
#    print("\nExiting...")
#finally:
#    app.oled.poweroff()