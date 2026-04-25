"""
M18 Battery Monitor
Displays: Pack Voltage, Cells, Usage Stats, and High-Current Histograms.
"""
from m18 import M18
from machine import Pin, SPI
import machine
import st7789 as st7789
import time
import gc

spi = machine.SPI(
    1,
    baudrate=80000000,
    polarity=0,
    phase=0,
    sck=machine.Pin(4),
    mosi=machine.Pin(6),
)
# ─── Helper: Draw Bar Chart ─────────────────────────────────────────
def draw_bar(screen, x, y, w, h, value, max_val, color=st7789.GREEN, bg=st7789.GRAY):
    """Draw a background bar and a filled value bar"""
    # Background
    screen.fill_rect(x, y, w, h, bg)
    # Value
    if max_val > 0:
        fill_w = int((value / max_val) * w)
        if fill_w > 0:
            screen.fill_rect(x, y, fill_w, h, color)
    # Border
    screen.rect(x, y, w, h, st7789.WHITE)

class App:
    def __init__(self):
        self.screen_idx = 0
        self.last_button_time = 0
        self.debounce_ms = 300
        self.health = None
        self.is_reading = False
        
        # ─── Hardware Init ──────────────────────────────────────────
        # Display SPI
        #self.spi_disp = SPI(1, baudrate=40000000, polarity=0, phase=0, sck=Pin(13), mosi=Pin(11))
        self.disp = st7789.ST7789(
            spi,
            240,      # Width
            240,      # Height
            reset=machine.Pin(3, machine.Pin.OUT),
            dc=machine.Pin(2, machine.Pin.OUT),
            cs=machine.Pin(7, machine.Pin.OUT),
            backlight=machine.Pin(10, machine.Pin.OUT),
            xstart=0,
            ystart=0
            )
        
        # Button on Pin 0 (active-low with internal pull-up)
        self.btn = machine.Pin(0, machine.Pin.IN, Pin.PULL_UP)
        
        # M18 Protocol
        self.m18 = M18(tx_pin=20, rx_pin=21, debug=False) # Debug off for speed
        
        # UI State
        self.disp.init(rotation=1)
        self.disp.backlight.value(1)
        self.disp.fill(st7789.BLACK)
        self.draw_ui_frame()
        self.update_data() # Initial read
        
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
        """Draw static UI elements (Buttons, Headers)"""
        self.disp.fill(st7789.BLACK)
        
        # Header Line
        #self.disp.line(0, 195, 319, 195, st7789.GRAY)
        
        # Buttons
        # Prev
        #self.disp.fill_rect(10, 205, 70, 30, st7789.DK_GRAY)
        #self.disp.draw_rect(10, 205, 70, 30, C_WHITE)
        #self.disp.text("PREV", 25, 215, st7789.RED, scale=1)
        
        # Read
        #self.disp.fill_rect(125, 205, 70, 30, st7789.DK_GRAY)
        #self.disp.draw_rect(125, 205, 70, 30, C_WHITE)
        #self.disp.text("READ", 135, 215, st7789.RED, scale=1)
        
        # Next
        #self.disp.fill_rect(240, 205, 70, 30, st7789.DK_GRAY)
        #self.disp.rect(240, 205, 70, 30, st7789.WHITE)
        #self.disp.text("NEXT", 255, 215, st7789.RED, scale=1)
        
        # Screen Title
        titles = ["PACK OVERVIEW", "MILWAUKEE", "USAGE HISTORY"]
        self.disp.text(titles[self.screen_idx], 10, 5, st7789.RED, scale=2)

    def update_data(self):
        """Fetch data from M18 BMS"""
        print("Reading M18...")
        self.disp.text("Reading...", 10, 20, st7789.YELLOW, scale=1)
        try:
            self.health = self.m18.get_health_lcd()
            self.update_display()
        except Exception as e:
            print("Error:", e)
            self.disp.text("Error Reading!", 10, 20, st7789.RED, scale=1)

    def update_display(self):
        """Render current screen index"""
        if not self.health: return
        
        h = self.health
        
        # Clear Data Area (below header, above buttons)
        self.disp.fill_rect(0, 20, 240, 175, st7789.BLACK)
        
        if self.screen_idx == 0:
            self.draw_screen_cells(h)
        elif self.screen_idx == 1:
            self.draw_screen_overview(h)
        elif self.screen_idx == 2:
            self.draw_screen_usage(h)

    def draw_screen_overview(self, h):
        # Big Voltage
        self.disp.text("{:.2f} V".format(h['total_v']), 10, 30, st7789.GREEN, scale=1)
        
        # Imbalance
        self.disp.text("Imbalance: {} mV".format(h['imbalance']), 10, 70, st7789.CYAN, scale=1)
        
        # Capacity
        self.disp.text("Total Discharged: {:.1f} Ah".format(h['total_ah']), 10, 90, st7789.WHITE, scale=1)
        
        # Days & Cycles
        self.disp.text("Days Active: {}".format(h['days_since_first']), 10, 110, st7789.CYAN, scale=1)
        self.disp.text("Years: {:.1f}".format(h['years']), 160, 110, st7789.CYAN, scale=1)
        self.disp.text("Total Charges: {}".format(h['charge_total']), 10, 130, st7789.WHITE, scale=1)
        
        # Redlink & LowV
        self.disp.text("Milwaukee Charges: {}".format(h['redlink_count']), 10, 150, st7789.CYAN, scale=1)
        self.disp.text("LowV Chg: {}".format(h['lowv_charge_count']), 10, 170, st7789.ORANGE, scale=1)

    def draw_screen_cells(self, h):
        cells = h['cells']
        colors = [st7789.GREEN if v > 3200 else st7789.RED for v in cells]
        
        y_start = 30
        for i, v in enumerate(cells):
            y = y_start + (i * 30)
            # Label
            self.disp.text( "Cell {}: ".format(i+1), 10, y,st7789.WHITE, scale=1)
            # Value
            self.disp.text("{} mV".format(v), 80, y, colors[i], scale=1)
            
            # Mini Bar (3.0V to 4.2V range)
            min_v = 3000; max_v = 4200
            pct = max(0, min(100, (v - min_v) / (max_v - min_v) * 100))
            draw_bar(self.disp, 10, y+12, 210, 8, pct, 100, colors[i], st7789.DK_GRAY)
            #draw_bar(self.disp, 10, y_pos+12, 200, 6, pct, 100, st7789.ORANGE, st7789.DK_GRAY)
    def draw_screen_usage(self, h):
        buckets = h['buckets'] # 20 buckets: 10-20A to 200-210A
        pcts = h['bucket_pct']
        total_sec = h['bucket_total_sec']
        
        self.disp.text("Discharge Histogram (10-200A)", 10, 30, st7789.WHITE, scale=1)
        self.disp.text("Total Time: {} min".format(total_sec//60), 10, 45, st7789.CYAN, scale=1)
        
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
            text = "{}: {}m ({}%)".format(amp_label, sec//60, pct)
            self.disp.text(text, 10, y_pos, st7789.WHITE, scale=1)
            
            # Bar
            draw_bar(self.disp, 10, y_pos+10, 200, 6, pct, 100, st7789.ORANGE, st7789.DK_GRAY)
            
            y_pos += 25

# ─── Main Loop ──────────────────────────────────────────────────────
#try:
app = App()
while True:
        # The touch library handles interrupts, but we can poll if needed
        # or just let the interrupt handler update state.
        # For stability, we just sleep. The touch handler updates the screen.
    #app.read_button()
    time.sleep_ms(10) 
    app.handle_input()    
#except KeyboardInterrupt:
#    print("\nExiting...")
#finally:
#    app.bl.off()
#    app.disp.cleanup()
#    self.disp.fill(st7789.BLACK)