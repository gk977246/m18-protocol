import machine
import st7789 as st7789
import time

# Initialize SPI
spi = machine.SPI(
    1,
    baudrate=80000000,
    polarity=0,
    phase=0,
    sck=machine.Pin(13),
    mosi=machine.Pin(11),
)

# Initialize display
display = st7789.ST7789(
    spi,
    240,      # Width
    320,      # Height
    reset=machine.Pin(9, machine.Pin.OUT),
    dc=machine.Pin(8, machine.Pin.OUT),
    cs=machine.Pin(10, machine.Pin.OUT),
    backlight=machine.Pin(7, machine.Pin.OUT),
    xstart=0,
    ystart=0
)

# Initialize with rotation
# Try rotation=0, 1, 2, or 3 to fix text direction
# 0=portrait, 1=landscape, 2=portrait flipped, 3=landscape flipped
display.init(rotation=0)

# Turn on backlight
display.backlight.value(1)

# Test 1: Fill screen with colors
print("Test 1: Colors")
display.fill(st7789.RED)
time.sleep(1)
display.fill(st7789.GREEN)
time.sleep(1)
display.fill(st7789.BLUE)
time.sleep(1)
display.fill(st7789.BLACK)

# Test 2: Draw some rectangles
print("Test 2: Rectangles")
display.fill(st7789.BLACK)
display.fill_rect(10, 10, 50, 50, st7789.RED)
display.fill_rect(70, 10, 50, 50, st7789.GREEN)
display.fill_rect(130, 10, 50, 50, st7789.BLUE)
time.sleep(2)

# Test 3: Draw text (LARGE scale to be readable)
print("Test 3: Large Text")
display.fill(st7789.BLACK)
display.text("Hello!", 10, 10, st7789.WHITE, scale=3)
time.sleep(2)

# Test 4: Even larger text
print("Test 4: Huge Text")
display.fill(st7789.BLUE)
display.text("ESP32", 10, 50, st7789.YELLOW, scale=4)
time.sleep(2)

# Test 5: Simple small bitmap (32x32)
print("Test 5: Small Bitmap")
display.fill(st7789.BLACK)

# Create a simple 32x32 gradient (only 2KB)
bitmap = bytearray()
for y in range(32):
    for x in range(32):
        # Simple gradient
        r = x * 8
        g = y * 8
        b = 128
        color = st7789.color565(r, g, b)
        bitmap.extend(color.to_bytes(2, 'big'))

display.draw_bitmap(bitmap, 50, 50, 32, 32)
display.text("32x32 Bitmap", 10, 100, st7789.WHITE, scale=2)
time.sleep(2)

# Test 6: Another small bitmap (64x64 checkerboard)
print("Test 6: Checkerboard")
display.fill(st7789.BLACK)

# Create 64x64 checkerboard (only 8KB)
bitmap2 = bytearray()
for y in range(64):
    for x in range(64):
        if (x // 8 + y // 8) % 2 == 0:
            color = st7789.WHITE
        else:
            color = st7789.RED
        bitmap2.extend(color.to_bytes(2, 'big'))

display.draw_bitmap(bitmap2, 88, 128, 64, 64)
display.text("64x64", 10, 150, st7789.CYAN, scale=2)
time.sleep(2)

# Test 7: Text with background
print("Test 7: Text with BG")
display.fill(st7789.BLACK)
display.text("TEXT", 10, 10, st7789.WHITE, st7789.BLUE, scale=5)
time.sleep(2)

# Test 8: Load and display BMP file (if it exists)
print("Test 8: BMP File")
# First, make sure you have uploaded a 24-bit BMP file to your ESP32-C6
# The BMP should be 240x320 pixels or smaller
# You can use a tool like ampy to upload: ampy put image.bmp

# Try to load and display a BMP file
if display.draw_bmp_file_streaming('beach.bmp', x=0, y=0):
    print("BMP displayed successfully!")
    # display.text("From BMP", 10, 10, st7789.WHITE, st7789.BLACK, scale=2)
    time.sleep(3)
else:
    print("BMP file not found or error loading")
    display.fill(st7789.BLACK)
    display.text("No BMP", 10, 50, st7789.RED, scale=3)
    display.text("Upload", 10, 100, st7789.RED, scale=3)
    display.text("img1.bmp", 10, 150, st7789.RED, scale=2)
    time.sleep(2)

print("Demo complete!")
print("Memory usage is low - only small bitmaps used")
print("")
print("To display BMP files:")
print("1. Create a 24-bit BMP (240x320 or smaller)")
print("2. Upload to ESP32: ampy --port /dev/ttyUSB0 put image.bmp")
print("3. Use: display.draw_bmp_file('image.bmp')")