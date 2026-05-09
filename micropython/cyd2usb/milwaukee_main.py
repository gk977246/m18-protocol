"""
M18 Battery Monitor for ILI9341 Display + XPT2046 Touch
Displays: Pack Voltage, Cells, Usage Stats, and High-Current Histograms.
"""
from m18 import M18
from ili9341 import Display, color565
from xpt2046 import Touch
from machine import Pin, SPI
import time
import gc

# ─── Color Palette ──────────────────────────────────────────────────
C_BLACK   = color565(0, 0, 0)
C_WHITE   = color565(255, 255, 255)
C_RED     = color565(255, 0, 0)
C_GREEN   = color565(0, 255, 0)
C_BLUE    = color565(0, 0, 255)
C_YELLOW  = color565(255, 255, 0)
C_CYAN    = color565(0, 255, 255)
C_GRAY    = color565(64, 64, 64)
C_DK_GRAY = color565(32, 32, 32)
C_ORANGE  = color565(255, 165, 0)

# ─── Helper: Draw Bar Chart ─────────────────────────────────────────
def draw_bar(screen, x, y, w, h, value, max_val, color=C_GREEN, bg=C_DK_GRAY):
    """Draw a background bar and a filled value bar"""
    # Background
    screen.fill_rectangle(x, y, w, h, bg)
    # Value
    if max_val > 0:
        fill_w = int((value / max_val) * w)
        if fill_w > 0:
            screen.fill_rectangle(x, y, fill_w, h, color)
    # Border
    screen.draw_rectangle(x, y, w, h, C_WHITE)

class App:
    def __init__(self):
        self.screen_idx = 0
        self.last_update = 0
        self.health = None
        self.is_reading = False
        
        # ─── Hardware Init ──────────────────────────────────────────
        # Display SPI
        self.spi_disp = SPI(1, baudrate=40000000, sck=Pin(14), mosi=Pin(13))
        self.disp = Display(self.spi_disp, dc=Pin(2), cs=Pin(15), rst=Pin(15),
                            width=320, height=240, bgr=False, gamma=True)
        
        # Backlight
        self.bl = Pin(21, Pin.OUT)
        self.bl.on()
        
        # Touch SPI
        self.spi_touch = SPI(2, baudrate=1000000, sck=Pin(25), mosi=Pin(32), miso=Pin(39))
        self.touch = Touch(self.spi_touch, cs=Pin(33), int_pin=Pin(36),
                           int_handler=self.on_touch)
        
        # M18 Protocol
        self.m18 = M18(tx_pin=22, rx_pin=27, debug=False) # Debug off for speed
        
        # UI State
        self.disp.clear(C_BLACK)
        self.draw_ui_frame()
        #self.update_data() # Initial read
        
    def on_touch(self, x, y):
        """Handle touch interrupts. Note: X/Y might be swapped depending on calibration."""
        # Simple debounce/state check could go here
        # For this demo, we rely on the main loop checking touch status or 
        # we use the touch library's built-in polling if available.
        # Since XPT2046 lib usually calls this handler, we set a flag.
        self.touched_x = x
        self.touched_y = y
        self.handle_input(x, y)

    def handle_input(self, tx, ty):
        """Map touch coordinates to buttons"""
        # Screen is 320x240. Buttons are at bottom (y > 200)
        if tx < 200: return # Ignore touches on data area
        
        # Button Zones (approximate based on draw_ui_frame)
        # Left: 0-80, Mid: 120-200, Right: 240-320
        
        if ty < 100:
            # PREV Button
            self.screen_idx = (self.screen_idx - 1) % 3
            self.draw_ui_frame() # Redraw frame to clear old data
            self.update_display()
            time.sleep_ms(300) # Debounce
            
        elif ty > 220:
            # NEXT Button
            self.screen_idx = (self.screen_idx + 1) % 3
            self.draw_ui_frame()
            self.update_display()
            time.sleep_ms(300)
            
        elif 120 < ty < 200:
            # READ Button (Force Refresh)
            self.update_data()
            time.sleep_ms(300)

    def draw_ui_frame(self):
        """Draw static UI elements (Buttons, Headers)"""
        self.disp.clear(C_BLACK)
        
        # Header Line
        self.disp.draw_line(0, 195, 319, 195, C_GRAY)
        
        # Buttons
        # Prev
        self.disp.fill_rectangle(10, 205, 70, 30, C_DK_GRAY)
        self.disp.draw_rectangle(10, 205, 70, 30, C_WHITE)
        self.disp.draw_text8x8(25, 215, "PREV", C_WHITE, C_DK_GRAY)
        
        # Read
        self.disp.fill_rectangle(125, 205, 70, 30, C_DK_GRAY)
        self.disp.draw_rectangle(125, 205, 70, 30, C_WHITE)
        self.disp.draw_text8x8(135, 215, "READ", C_YELLOW, C_DK_GRAY)
        
        # Next
        self.disp.fill_rectangle(240, 205, 70, 30, C_DK_GRAY)
        self.disp.draw_rectangle(240, 205, 70, 30, C_WHITE)
        self.disp.draw_text8x8(255, 215, "NEXT", C_WHITE, C_DK_GRAY)
        
        # Screen Title
        titles = ["MILWAUKEE", "PACK OVERVIEW", "USAGE & HISTOGRAM"]
        self.disp.draw_text8x8(10, 5, titles[self.screen_idx], C_RED, C_BLACK)

    def update_data(self):
        """Fetch data from M18 BMS"""
        print("Reading M18...")
        self.disp.draw_text8x8(10, 20, "Reading...", C_YELLOW, C_BLACK)
        try:
            self.health = self.m18.get_health_lcd()
            self.update_display()
        except Exception as e:
            print("Error:", e)
            self.disp.draw_text8x8(10, 20, "Error Reading!", C_RED, C_BLACK)

    def update_display(self):
        """Render current screen index"""
        if not self.health: return
        
        h = self.health
        
        # Clear Data Area (below header, above buttons)
        self.disp.fill_rectangle(0, 20, 319, 175, C_BLACK)
        
        if self.screen_idx == 0:
            self.draw_screen_cells(h)
        elif self.screen_idx == 1:
            self.draw_screen_overview(h)
        elif self.screen_idx == 2:
            self.draw_screen_usage(h)

    def draw_screen_overview(self, h):
        # Big Voltage
        self.disp.draw_text8x8(10, 30, "{:.2f} V".format(h['total_v']), C_GREEN, C_BLACK)
        
        # Imbalance
        self.disp.draw_text8x8(10, 70, "Imbalance: {} mV".format(h['imbalance']), C_CYAN, C_BLACK)
        
        # Capacity
        self.disp.draw_text8x8(10, 90, "Total Discharged: {:.1f} Ah".format(h['total_ah']), C_WHITE, C_BLACK)
        
        # Days & Cycles
        self.disp.draw_text8x8(10, 110, "Days Active: {}".format(h['days_since_first']), C_CYAN, C_BLACK)
        self.disp.draw_text8x8(160, 110, "Years: {:.1f}".format(h['years']), C_CYAN, C_BLACK)
        self.disp.draw_text8x8(10, 130, "Total Charges: {}".format(h['charge_total']), C_WHITE, C_BLACK)
        
        # Redlink & LowV
        self.disp.draw_text8x8(10, 150, "Milwaukee Charges: {}".format(h['redlink_count']), C_CYAN, C_BLACK)
        self.disp.draw_text8x8(10, 170, "LowV Chg: {}".format(h['lowv_charge_count']), C_ORANGE, C_BLACK)

    def draw_screen_cells(self, h):
        cells = h['cells']
        colors = [C_GREEN if v > 3000 else C_RED for v in cells]
        
        y_start = 40
        for i, v in enumerate(cells):
            y = y_start + (i * 30)
            # Label
            self.disp.draw_text8x8(20, y, "Cell {}: ".format(i+1), C_WHITE, C_BLACK)
            # Value
            self.disp.draw_text8x8(100, y, "{} mV".format(v), colors[i], C_BLACK)
            
            # Mini Bar (3.0V to 4.2V range)
            min_v = 3000; max_v = 4200
            pct = max(0, min(100, (v - min_v) / (max_v - min_v) * 100))
            draw_bar(self.disp, 180, y+2, 120, 10, pct, 100, colors[i], C_DK_GRAY)

    def draw_screen_usage(self, h):
        buckets = h['buckets'] # 20 buckets: 10-20A to 200-210A
        pcts = h['bucket_pct']
        total_sec = h['bucket_total_sec']
        
        self.disp.draw_text8x8(10, 30, "Discharge Histogram (10-200A)", C_WHITE, C_BLACK)
        self.disp.draw_text8x8(10, 45, "Total Time: {} min".format(total_sec//60), C_CYAN, C_BLACK)
        
        # Draw Histogram
        # We have 11 buckets. Let's show top 5 or all if they fit.
        # Layout: 2 columns of bars? Or just list top 5.
        
        # Let's list top 5 buckets by usage
        indexed = list(enumerate(zip(buckets, pcts)))
        indexed.sort(key=lambda x: x[1][0], reverse=True)
        
        y_pos = 65
        for i in range(min(6, len(indexed))):
            idx, (sec, pct) = indexed[i]
            amp_label = "{}-{}A".format((idx+1)*10, (idx+2)*10)
            
            # Text
            text = "{}: {}min ({}%)".format(amp_label, sec//60, pct)
            self.disp.draw_text8x8(10, y_pos, text, C_WHITE, C_BLACK)
            
            # Bar
            draw_bar(self.disp, 10, y_pos+12, 200, 6, pct, 100, C_ORANGE, C_DK_GRAY)
            
            y_pos += 20

# ─── Main Loop ──────────────────────────────────────────────────────
try:
    app = App()
    while True:
        # The touch library handles interrupts, but we can poll if needed
        # or just let the interrupt handler update state.
        # For stability, we just sleep. The touch handler updates the screen.
        time.sleep(0.1)
        
except KeyboardInterrupt:
    print("\nExiting...")
finally:
    app.bl.off()
    app.disp.cleanup()
