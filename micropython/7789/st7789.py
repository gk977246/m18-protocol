import time
from micropython import const
import ustruct as struct

# commands
ST77XX_NOP = const(0x00)
ST77XX_SWRESET = const(0x01)
ST77XX_RDDID = const(0x04)
ST77XX_RDDST = const(0x09)

ST77XX_SLPIN = const(0x10)
ST77XX_SLPOUT = const(0x11)
ST77XX_PTLON = const(0x12)
ST77XX_NORON = const(0x13)

ST77XX_INVOFF = const(0x20)
ST77XX_INVON = const(0x21)
ST77XX_DISPOFF = const(0x28)
ST77XX_DISPON = const(0x29)
ST77XX_CASET = const(0x2A)
ST77XX_RASET = const(0x2B)
ST77XX_RAMWR = const(0x2C)
ST77XX_RAMRD = const(0x2E)

ST77XX_PTLAR = const(0x30)
ST77XX_COLMOD = const(0x3A)
ST7789_MADCTL = const(0x36)

ST7789_MADCTL_MY = const(0x80)
ST7789_MADCTL_MX = const(0x40)
ST7789_MADCTL_MV = const(0x20)
ST7789_MADCTL_ML = const(0x10)
ST7789_MADCTL_BGR = const(0x08)
ST7789_MADCTL_MH = const(0x04)
ST7789_MADCTL_RGB = const(0x00)

ST7789_RDID1 = const(0xDA)
ST7789_RDID2 = const(0xDB)
ST7789_RDID3 = const(0xDC)
ST7789_RDID4 = const(0xDD)

ColorMode_65K = const(0x50)
ColorMode_262K = const(0x60)
ColorMode_12bit = const(0x03)
ColorMode_16bit = const(0x05)
ColorMode_18bit = const(0x06)
ColorMode_16M = const(0x07)

# Color definitions
BLACK = const(0x0000)
BLUE = const(0x001F)
RED = const(0xF800)
GREEN = const(0x07E0)
CYAN = const(0x07FF)
MAGENTA = const(0xF81F)
YELLOW = const(0xFFE0)
ORANGE = const(0xFC00)
WHITE = const(0xFFFF)
GRAY = const(0xD69A)
DK_GRAY = const(0x7BEF)

_ENCODE_PIXEL = ">H"
_ENCODE_POS = ">HH"
_DECODE_PIXEL = ">BBB"

_BUFFER_SIZE = const(256)


def delay_ms(ms):
    time.sleep_ms(ms)


def color565(r, g=0, b=0):
    """Convert red, green and blue values (0-255) into a 16-bit 565 encoding."""
    try:
        r, g, b = r  # see if the first var is a tuple/list
    except TypeError:
        pass
    return (r & 0xf8) << 8 | (g & 0xfc) << 3 | b >> 3


# Simple 8x8 font (ASCII 32-127)
FONT_8X8 = [
    [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],  # Space
    [0x18, 0x3C, 0x3C, 0x18, 0x18, 0x00, 0x18, 0x00],  # !
    [0x36, 0x36, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],  # "
    [0x36, 0x36, 0x7F, 0x36, 0x7F, 0x36, 0x36, 0x00],  # #
    [0x0C, 0x3E, 0x03, 0x1E, 0x30, 0x1F, 0x0C, 0x00],  # $
    [0x00, 0x63, 0x33, 0x18, 0x0C, 0x66, 0x63, 0x00],  # %
    [0x1C, 0x36, 0x1C, 0x6E, 0x3B, 0x33, 0x6E, 0x00],  # &
    [0x06, 0x06, 0x03, 0x00, 0x00, 0x00, 0x00, 0x00],  # '
    [0x18, 0x0C, 0x06, 0x06, 0x06, 0x0C, 0x18, 0x00],  # (
    [0x06, 0x0C, 0x18, 0x18, 0x18, 0x0C, 0x06, 0x00],  # )
    [0x00, 0x66, 0x3C, 0xFF, 0x3C, 0x66, 0x00, 0x00],  # *
    [0x00, 0x0C, 0x0C, 0x3F, 0x0C, 0x0C, 0x00, 0x00],  # +
    [0x00, 0x00, 0x00, 0x00, 0x00, 0x0C, 0x0C, 0x06],  # ,
    [0x00, 0x00, 0x00, 0x3F, 0x00, 0x00, 0x00, 0x00],  # -
    [0x00, 0x00, 0x00, 0x00, 0x00, 0x0C, 0x0C, 0x00],  # .
    [0x60, 0x30, 0x18, 0x0C, 0x06, 0x03, 0x01, 0x00],  # /
    [0x3E, 0x63, 0x73, 0x7B, 0x6F, 0x67, 0x3E, 0x00],  # 0
    [0x0C, 0x0E, 0x0C, 0x0C, 0x0C, 0x0C, 0x3F, 0x00],  # 1
    [0x1E, 0x33, 0x30, 0x1C, 0x06, 0x33, 0x3F, 0x00],  # 2
    [0x1E, 0x33, 0x30, 0x1C, 0x30, 0x33, 0x1E, 0x00],  # 3
    [0x38, 0x3C, 0x36, 0x33, 0x7F, 0x30, 0x78, 0x00],  # 4
    [0x3F, 0x03, 0x1F, 0x30, 0x30, 0x33, 0x1E, 0x00],  # 5
    [0x1C, 0x06, 0x03, 0x1F, 0x33, 0x33, 0x1E, 0x00],  # 6
    [0x3F, 0x33, 0x30, 0x18, 0x0C, 0x0C, 0x0C, 0x00],  # 7
    [0x1E, 0x33, 0x33, 0x1E, 0x33, 0x33, 0x1E, 0x00],  # 8
    [0x1E, 0x33, 0x33, 0x3E, 0x30, 0x18, 0x0E, 0x00],  # 9
    [0x00, 0x0C, 0x0C, 0x00, 0x00, 0x0C, 0x0C, 0x00],  # :
    [0x00, 0x0C, 0x0C, 0x00, 0x00, 0x0C, 0x0C, 0x06],  # ;
    [0x18, 0x0C, 0x06, 0x03, 0x06, 0x0C, 0x18, 0x00],  # <
    [0x00, 0x00, 0x3F, 0x00, 0x00, 0x3F, 0x00, 0x00],  # =
    [0x06, 0x0C, 0x18, 0x30, 0x18, 0x0C, 0x06, 0x00],  # >
    [0x1E, 0x33, 0x30, 0x18, 0x0C, 0x00, 0x0C, 0x00],  # ?
    [0x3E, 0x63, 0x7B, 0x7B, 0x7B, 0x03, 0x1E, 0x00],  # @
    [0x0C, 0x1E, 0x33, 0x33, 0x3F, 0x33, 0x33, 0x00],  # A
    [0x3F, 0x66, 0x66, 0x3E, 0x66, 0x66, 0x3F, 0x00],  # B
    [0x3C, 0x66, 0x03, 0x03, 0x03, 0x66, 0x3C, 0x00],  # C
    [0x1F, 0x36, 0x66, 0x66, 0x66, 0x36, 0x1F, 0x00],  # D
    [0x7F, 0x46, 0x16, 0x1E, 0x16, 0x46, 0x7F, 0x00],  # E
    [0x7F, 0x46, 0x16, 0x1E, 0x16, 0x06, 0x0F, 0x00],  # F
    [0x3C, 0x66, 0x03, 0x03, 0x73, 0x66, 0x7C, 0x00],  # G
    [0x33, 0x33, 0x33, 0x3F, 0x33, 0x33, 0x33, 0x00],  # H
    [0x1E, 0x0C, 0x0C, 0x0C, 0x0C, 0x0C, 0x1E, 0x00],  # I
    [0x78, 0x30, 0x30, 0x30, 0x33, 0x33, 0x1E, 0x00],  # J
    [0x67, 0x66, 0x36, 0x1E, 0x36, 0x66, 0x67, 0x00],  # K
    [0x0F, 0x06, 0x06, 0x06, 0x46, 0x66, 0x7F, 0x00],  # L
    [0x63, 0x77, 0x7F, 0x7F, 0x6B, 0x63, 0x63, 0x00],  # M
    [0x63, 0x67, 0x6F, 0x7B, 0x73, 0x63, 0x63, 0x00],  # N
    [0x1C, 0x36, 0x63, 0x63, 0x63, 0x36, 0x1C, 0x00],  # O
    [0x3F, 0x66, 0x66, 0x3E, 0x06, 0x06, 0x0F, 0x00],  # P
    [0x1E, 0x33, 0x33, 0x33, 0x3B, 0x1E, 0x38, 0x00],  # Q
    [0x3F, 0x66, 0x66, 0x3E, 0x36, 0x66, 0x67, 0x00],  # R
    [0x1E, 0x33, 0x07, 0x0E, 0x38, 0x33, 0x1E, 0x00],  # S
    [0x3F, 0x2D, 0x0C, 0x0C, 0x0C, 0x0C, 0x1E, 0x00],  # T
    [0x33, 0x33, 0x33, 0x33, 0x33, 0x33, 0x3F, 0x00],  # U
    [0x33, 0x33, 0x33, 0x33, 0x33, 0x1E, 0x0C, 0x00],  # V
    [0x63, 0x63, 0x63, 0x6B, 0x7F, 0x77, 0x63, 0x00],  # W
    [0x63, 0x63, 0x36, 0x1C, 0x1C, 0x36, 0x63, 0x00],  # X
    [0x33, 0x33, 0x33, 0x1E, 0x0C, 0x0C, 0x1E, 0x00],  # Y
    [0x7F, 0x63, 0x31, 0x18, 0x4C, 0x66, 0x7F, 0x00],  # Z
    [0x1E, 0x06, 0x06, 0x06, 0x06, 0x06, 0x1E, 0x00],  # [
    [0x03, 0x06, 0x0C, 0x18, 0x30, 0x60, 0x40, 0x00],  # \
    [0x1E, 0x18, 0x18, 0x18, 0x18, 0x18, 0x1E, 0x00],  # ]
    [0x08, 0x1C, 0x36, 0x63, 0x00, 0x00, 0x00, 0x00],  # ^
    [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xFF],  # _
    [0x0C, 0x0C, 0x18, 0x00, 0x00, 0x00, 0x00, 0x00],  # `
    [0x00, 0x00, 0x1E, 0x30, 0x3E, 0x33, 0x6E, 0x00],  # a
    [0x07, 0x06, 0x06, 0x3E, 0x66, 0x66, 0x3B, 0x00],  # b
    [0x00, 0x00, 0x1E, 0x33, 0x03, 0x33, 0x1E, 0x00],  # c
    [0x38, 0x30, 0x30, 0x3e, 0x33, 0x33, 0x6E, 0x00],  # d
    [0x00, 0x00, 0x1E, 0x33, 0x3f, 0x03, 0x1E, 0x00],  # e
    [0x1C, 0x36, 0x06, 0x0f, 0x06, 0x06, 0x0F, 0x00],  # f
    [0x00, 0x00, 0x6E, 0x33, 0x33, 0x3E, 0x30, 0x1F],  # g
    [0x07, 0x06, 0x36, 0x6E, 0x66, 0x66, 0x67, 0x00],  # h
    [0x0C, 0x00, 0x0E, 0x0C, 0x0C, 0x0C, 0x1E, 0x00],  # i
    [0x30, 0x00, 0x30, 0x30, 0x30, 0x33, 0x33, 0x1E],  # j
    [0x07, 0x06, 0x66, 0x36, 0x1E, 0x36, 0x67, 0x00],  # k
    [0x0E, 0x0C, 0x0C, 0x0C, 0x0C, 0x0C, 0x1E, 0x00],  # l
    [0x00, 0x00, 0x33, 0x7F, 0x7F, 0x6B, 0x63, 0x00],  # m
    [0x00, 0x00, 0x1F, 0x33, 0x33, 0x33, 0x33, 0x00],  # n
    [0x00, 0x00, 0x1E, 0x33, 0x33, 0x33, 0x1E, 0x00],  # o
    [0x00, 0x00, 0x3B, 0x66, 0x66, 0x3E, 0x06, 0x0F],  # p
    [0x00, 0x00, 0x6E, 0x33, 0x33, 0x3E, 0x30, 0x78],  # q
    [0x00, 0x00, 0x3B, 0x6E, 0x66, 0x06, 0x0F, 0x00],  # r
    [0x00, 0x00, 0x3E, 0x03, 0x1E, 0x30, 0x1F, 0x00],  # s
    [0x08, 0x0C, 0x3E, 0x0C, 0x0C, 0x2C, 0x18, 0x00],  # t
    [0x00, 0x00, 0x33, 0x33, 0x33, 0x33, 0x6E, 0x00],  # u
    [0x00, 0x00, 0x33, 0x33, 0x33, 0x1E, 0x0C, 0x00],  # v
    [0x00, 0x00, 0x63, 0x6B, 0x7F, 0x7F, 0x36, 0x00],  # w
    [0x00, 0x00, 0x63, 0x36, 0x1C, 0x36, 0x63, 0x00],  # x
    [0x00, 0x00, 0x33, 0x33, 0x33, 0x3E, 0x30, 0x1F],  # y
    [0x00, 0x00, 0x3F, 0x19, 0x0C, 0x26, 0x3F, 0x00],  # z
    [0x38, 0x0C, 0x0C, 0x07, 0x0C, 0x0C, 0x38, 0x00],  # {
    [0x18, 0x18, 0x18, 0x00, 0x18, 0x18, 0x18, 0x00],  # |
    [0x07, 0x0C, 0x0C, 0x38, 0x0C, 0x0C, 0x07, 0x00],  # }
    [0x6E, 0x3B, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],  # ~
]


class ST77xx:
    def __init__(self, spi, width, height, reset, dc, cs=None, backlight=None,
                 xstart=-1, ystart=-1):
        """
        display = st7789.ST7789(
            SPI(1, baudrate=40000000, phase=0, polarity=1),
            240, 240,
            reset=machine.Pin(5, machine.Pin.OUT),
            dc=machine.Pin(2, machine.Pin.OUT),
        )

        """
        self.width = width
        self.height = height
        self.spi = spi
        if spi is None:
            import machine
            self.spi = machine.SPI(1, baudrate=40000000, phase=0, polarity=1)
        self.reset = reset
        self.dc = dc
        self.cs = cs
        self.backlight = backlight
        if xstart >= 0 and ystart >= 0:
            self.xstart = xstart
            self.ystart = ystart
        elif (self.width, self.height) == (240, 240):
            self.xstart = 0
            self.ystart = 0
        elif (self.width, self.height) == (135, 240):
            self.xstart = 52
            self.ystart = 40
        else:
            # Default to 0,0 for other sizes like 240x320
            self.xstart = 0
            self.ystart = 0

    def dc_low(self):
        self.dc.off()

    def dc_high(self):
        self.dc.on()

    def reset_low(self):
        if self.reset:
            self.reset.off()

    def reset_high(self):
        if self.reset:
            self.reset.on()

    def cs_low(self):
        if self.cs:
            self.cs.off()

    def cs_high(self):
        if self.cs:
            self.cs.on()

    def write(self, command=None, data=None):
        """SPI write to the device: commands and data"""
        self.cs_low()
        if command is not None:
            self.dc_low()
            self.spi.write(bytes([command]))
        if data is not None:
            self.dc_high()
            self.spi.write(data)
        self.cs_high()

    def hard_reset(self):
        self.cs_low()
        self.reset_high()
        delay_ms(50)
        self.reset_low()
        delay_ms(50)
        self.reset_high()
        delay_ms(150)
        self.cs_high()

    def soft_reset(self):
        self.write(ST77XX_SWRESET)
        delay_ms(150)

    def sleep_mode(self, value):
        if value:
            self.write(ST77XX_SLPIN)
        else:
            self.write(ST77XX_SLPOUT)

    def inversion_mode(self, value):
        if value:
            self.write(ST77XX_INVON)
        else:
            self.write(ST77XX_INVOFF)

    def _set_color_mode(self, mode):
        self.write(ST77XX_COLMOD, bytes([mode & 0x77]))

    def init(self, *args, **kwargs):
        self.hard_reset()
        self.soft_reset()
        self.sleep_mode(False)

    def _set_mem_access_mode(self, rotation, vert_mirror, horz_mirror, is_bgr):
        rotation &= 7
        value = {
            0: 0,
            1: ST7789_MADCTL_MX,
            2: ST7789_MADCTL_MY,
            3: ST7789_MADCTL_MX | ST7789_MADCTL_MY,
            4: ST7789_MADCTL_MV,
            5: ST7789_MADCTL_MV | ST7789_MADCTL_MX,
            6: ST7789_MADCTL_MV | ST7789_MADCTL_MY,
            7: ST7789_MADCTL_MV | ST7789_MADCTL_MX | ST7789_MADCTL_MY,
        }[rotation]

        if vert_mirror:
            value = ST7789_MADCTL_ML
        elif horz_mirror:
            value = ST7789_MADCTL_MH

        if is_bgr:
            value |= ST7789_MADCTL_BGR
        self.write(ST7789_MADCTL, bytes([value]))

    def _encode_pos(self, x, y):
        """Encode a postion into bytes."""
        return struct.pack(_ENCODE_POS, x, y)

    def _encode_pixel(self, color):
        """Encode a pixel color into bytes."""
        return struct.pack(_ENCODE_PIXEL, color)

    def _set_columns(self, start, end):
        if start > end or end >= self.width:
            return
        start += self.xstart
        end += self.xstart
        self.write(ST77XX_CASET, self._encode_pos(start, end))

    def _set_rows(self, start, end):
        if start > end or end >= self.height:
            return
        start += self.ystart
        end += self.ystart
        self.write(ST77XX_RASET, self._encode_pos(start, end))

    def set_window(self, x0, y0, x1, y1):
        self._set_columns(x0, x1)
        self._set_rows(y0, y1)
        self.write(ST77XX_RAMWR)

    def vline(self, x, y, length, color):
        self.fill_rect(x, y, 1, length, color)

    def hline(self, x, y, length, color):
        self.fill_rect(x, y, length, 1, color)

    def pixel(self, x, y, color):
        self.set_window(x, y, x, y)
        self.write(None, self._encode_pixel(color))

    def blit_buffer(self, buffer, x, y, width, height):
        self.set_window(x, y, x + width - 1, y + height - 1)
        self.write(None, buffer)

    def rect(self, x, y, w, h, color):
        self.hline(x, y, w, color)
        self.vline(x, y, h, color)
        self.vline(x + w - 1, y, h, color)
        self.hline(x, y + h - 1, w, color)

    def fill_rect(self, x, y, width, height, color):
        self.set_window(x, y, x + width - 1, y + height - 1)
        chunks, rest = divmod(width * height, _BUFFER_SIZE)
        pixel = self._encode_pixel(color)
        self.dc_high()
        if chunks:
            data = pixel * _BUFFER_SIZE
            for _ in range(chunks):
                self.write(None, data)
        if rest:
            self.write(None, pixel * rest)

    def fill(self, color):
        self.fill_rect(0, 0, self.width, self.height, color)

    def line(self, x0, y0, x1, y1, color):
        # Line drawing function.  Will draw a single pixel wide line starting at
        # x0, y0 and ending at x1, y1.
        steep = abs(y1 - y0) > abs(x1 - x0)
        if steep:
            x0, y0 = y0, x0
            x1, y1 = y1, x1
        if x0 > x1:
            x0, x1 = x1, x0
            y0, y1 = y1, y0
        dx = x1 - x0
        dy = abs(y1 - y0)
        err = dx // 2
        if y0 < y1:
            ystep = 1
        else:
            ystep = -1
        while x0 <= x1:
            if steep:
                self.pixel(y0, x0, color)
            else:
                self.pixel(x0, y0, color)
            err -= dy
            if err < 0:
                y0 += ystep
                err += dx
            x0 += 1

    def char(self, char, x, y, color, bg_color=None, scale=1):
        """
        Draw a single character using the built-in 8x8 font.
        
        Args:
            char: Character to draw
            x, y: Top-left position
            color: Foreground color (RGB565)
            bg_color: Background color (RGB565), None for transparent
            scale: Scale factor (1=8x8, 2=16x16, etc.)
        """
        char_index = ord(char) - 32  # ASCII offset
        if char_index < 0 or char_index >= len(FONT_8X8):
            return  # Character not in font
        
        glyph = FONT_8X8[char_index]
        
        for row in range(8):
            for col in range(8):
                # Fixed: Read bits from left to right (bit 7 to bit 0)
                if glyph[row] & (1 << col):
                    # Draw foreground pixel
                    if scale == 1:
                        self.pixel(x + col, y + row, color)
                    else:
                        self.fill_rect(x + col * scale, y + row * scale, 
                                     scale, scale, color)
                elif bg_color is not None:
                    # Draw background pixel
                    if scale == 1:
                        self.pixel(x + col, y + row, bg_color)
                    else:
                        self.fill_rect(x + col * scale, y + row * scale,
                                     scale, scale, bg_color)

    def text(self, text, x, y, color, bg_color=None, scale=1):
        """
        Draw text using the built-in 8x8 font.
        
        Args:
            text: String to draw
            x, y: Top-left position
            color: Foreground color (RGB565)
            bg_color: Background color (RGB565), None for transparent
            scale: Scale factor (1=8x8, 2=16x16, etc.)
        """
        cursor_x = x
        for char in text:
            if char == '\n':
                y += 8 * scale
                cursor_x = x
            else:
                self.char(char, cursor_x, y, color, bg_color, scale)
                cursor_x += 8 * scale

    def draw_bitmap(self, bitmap_data, x=0, y=0, width=None, height=None):
        """
        Draw a bitmap image to the display.
        
        Args:
            bitmap_data: Bytes or bytearray containing RGB565 pixel data
                        (2 bytes per pixel, big-endian format)
            x, y: Top-left position to draw the bitmap
            width: Width of the bitmap (defaults to display width)
            height: Height of the bitmap (defaults to display height)
        
        Format: Each pixel is 2 bytes in RGB565 format (big-endian):
                RRRRRGGG GGGBBBBB
        
        Example for creating bitmap data:
            # Create a simple 2x2 red square
            bitmap = bytearray([
                0xF8, 0x00,  # Red pixel (0xF800)
                0xF8, 0x00,  # Red pixel
                0xF8, 0x00,  # Red pixel
                0xF8, 0x00,  # Red pixel
            ])
            display.draw_bitmap(bitmap, 0, 0, 2, 2)
        """
        if width is None:
            width = self.width
        if height is None:
            height = self.height
        
        # Ensure bitmap data is the correct size
        expected_size = width * height * 2  # 2 bytes per pixel
        if len(bitmap_data) < expected_size:
            raise ValueError(f"Bitmap data too small. Expected {expected_size} bytes, got {len(bitmap_data)}")
        
        # Draw the bitmap
        self.blit_buffer(bitmap_data, x, y, width, height)

    def draw_bitmap_chunked(self, bitmap_data, x=0, y=0, width=None, height=None, chunk_height=8):
        """
        Draw a large bitmap in chunks to save memory.
        Useful for full-screen images on memory-constrained devices.
        
        Args:
            bitmap_data: Bytes or bytearray containing RGB565 pixel data
            x, y: Top-left position
            width: Width of the bitmap
            height: Height of the bitmap
            chunk_height: Number of rows to draw at once (smaller = less memory)
        """
        if width is None:
            width = self.width
        if height is None:
            height = self.height
        
        bytes_per_row = width * 2  # 2 bytes per pixel
        
        for row in range(0, height, chunk_height):
            rows_in_chunk = min(chunk_height, height - row)
            chunk_size = rows_in_chunk * bytes_per_row
            start_byte = row * bytes_per_row
            end_byte = start_byte + chunk_size
            
            chunk = bitmap_data[start_byte:end_byte]
            self.blit_buffer(chunk, x, y + row, width, rows_in_chunk)

    def draw_bmp_file_streaming(self, filename, x=0, y=0, lines_per_chunk=4):
        """
        Load and draw a BMP file by streaming it line-by-line.
        Very memory efficient - only loads a few lines at a time.
        Only supports 24-bit uncompressed BMP files.
        
        Args:
            filename: Path to BMP file
            x, y: Position to draw
            lines_per_chunk: Number of lines to read at once (lower = less memory)
        """
        try:
            with open(filename, 'rb') as f:
                # Read BMP header
                header = f.read(14)
                if header[0:2] != b'BM':
                    print("Not a BMP file")
                    return False
                
                # Read DIB header
                dib_header = f.read(40)
                width = int.from_bytes(dib_header[4:8], 'little')
                height = int.from_bytes(dib_header[8:12], 'little')
                bits_per_pixel = int.from_bytes(dib_header[14:16], 'little')
                
                print(f"BMP: {width}x{height}, {bits_per_pixel}-bit")
                
                if bits_per_pixel != 24:
                    print(f"Only 24-bit BMP supported")
                    return False
                
                # Calculate padding
                row_size = ((width * 3 + 3) // 4) * 4
                padding = row_size - width * 3
                
                # Get pixel data offset
                pixel_offset = int.from_bytes(header[10:14], 'little')
                
                # BMP is stored bottom-to-top, so we read from bottom
                # Process in chunks to save memory
                for chunk_start in range(0, height, lines_per_chunk):
                    chunk_lines = min(lines_per_chunk, height - chunk_start)
                    chunk_data = bytearray()
                    
                    # Read lines for this chunk (in reverse order due to BMP format)
                    for line_in_chunk in range(chunk_lines):
                        line_idx = height - 1 - (chunk_start + line_in_chunk)
                        
                        # Seek to this line
                        line_offset = pixel_offset + (line_idx * row_size)
                        f.seek(line_offset)
                        
                        # Read one line and convert to RGB565
                        for px in range(width):
                            b = ord(f.read(1))
                            g = ord(f.read(1))
                            r = ord(f.read(1))
                            # Convert BGR888 to RGB565
                            rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
                            chunk_data.extend(rgb565.to_bytes(2, 'big'))
                    
                    # Draw this chunk
                    self.blit_buffer(chunk_data, x, y + chunk_start, width, chunk_lines)
                    
                    # Optional: Print progress
                    if chunk_start % 40 == 0:
                        print(f"Drawing: {chunk_start}/{height}")
                
                print("BMP loaded successfully!")
                return True
                
        except Exception as e:
            print(f"Error loading BMP: {e}")
            return False

    def draw_bmp_file(self, filename, x=0, y=0):
        """
        Load and draw a BMP file using streaming (memory efficient).
        Only supports 24-bit uncompressed BMP files.
        """
        return self.draw_bmp_file_streaming(filename, x, y, lines_per_chunk=4)

    def draw_bmp_file_chunked(self, filename, x=0, y=0, chunk_height=4):
        """
        Alias for draw_bmp_file_streaming for backward compatibility.
        """
        return self.draw_bmp_file_streaming(filename, x, y, lines_per_chunk=chunk_height)


class ST7789(ST77xx):
    def init(self, *, color_mode=ColorMode_65K | ColorMode_16bit, rotation=0):
        super().init()
        self._set_color_mode(color_mode)
        delay_ms(50)
        # Set rotation: 0=portrait, 1=landscape, 2=portrait flipped, 3=landscape flipped
        self.set_rotation(rotation)
        self.inversion_mode(True)
        delay_ms(10)
        self.write(ST77XX_NORON)
        delay_ms(10)
        self.fill(0)
        self.write(ST77XX_DISPON)
        delay_ms(500)
    
    def set_rotation(self, rotation):
        """Set display rotation: 0, 1, 2, or 3"""
        rotation = rotation % 4
        if rotation == 0:
            # Portrait mode
            self._set_mem_access_mode(0, False, False, False)
        elif rotation == 1:
            # Landscape mode
            self._set_mem_access_mode(5, False, False, False)
        elif rotation == 2:
            # Portrait flipped
            self._set_mem_access_mode(3, False, False, False)
        elif rotation == 3:
            # Landscape flipped
            self._set_mem_access_mode(6, False, False, False)