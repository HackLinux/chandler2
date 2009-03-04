#   Copyright (c) 2003-2007 Open Source Applications Foundation
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.


import wx
#import random
from itertools import izip, cycle
from struct import pack


from colorsys import hsv_to_rgb, rgb_to_hsv
#import Styles

def color2rgb(red, green, blue):
    return red/255.0, green/255.0, blue/255.0

def rgb2color(r, g, b):
    return int(r*255), int(g*255), int(b*255)

def SetTextColorsAndFont(grid, attr, dc, isSelected):
    """
      Set the text foreground, text background, brush and font into the dc
      for grids
    """
    if grid.IsEnabled():
        if isSelected:
            background = grid.GetSelectionBackground()
            foreground = grid.GetSelectionForeground()
        else:
            background = attr.GetBackgroundColour()
            foreground = attr.GetTextColour()
    else:
        background = wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE)
        foreground = wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT)
    dc.SetTextBackground(background)
    dc.SetTextForeground(foreground)
    dc.SetBrush(wx.Brush(background, wx.SOLID))

    dc.SetFont(attr.GetFont())

def DrawClippedTextWithDots(dc, text, rect, alignRight=False, top=None):
    rectX = rect.x + 1
    rectY = rect.y
    rowHeight = rect.GetHeight()

    # test for flicker by drawing a random character first each time we draw
    # line = chr(ord('a') + random.randint(0,25)) + line

    lineWidth, lineHeight = dc.GetTextExtent(text)
    if alignRight:
        x = rect.x + rect.width - lineWidth - 1
    else:
        x = rectX

    if top is None:
        y = rectY + (rowHeight - lineHeight) / 2
    else:
        y = rectY + top

    dc.DrawText(text, x, y)

    # If the text doesn't fit within the box we want to clip it and
    # put '...' at the end.  This method may chop a character in half,
    # but is a lot faster than doing the proper calculation of where
    # to cut off the text.  Eventually we will want a solution that
    # doesn't chop chars, but that will come along with multiline 
    # wrapping and hopefully won't be done at the python level.
    if lineWidth > rect.width - 2:
        width, height = dc.GetTextExtent('...')
        x = rect.x + rect.width - width - 1
        dc.DrawRectangle(x, y, width + 1, height)
        dc.DrawText('...', x, y)
        lineWidth = 0 # note that we filled it.

    return lineWidth


def DrawWrappedText(dc, text, rect):
    """
    Simple wordwrap - draws the text into the current DC

    returns the height of the text that was written

    measurements is a FontMeasurements object as returned by
    Styles.getMeasurements()
    """

    lineHeight = dc.GetTextExtent("M")[1]
    spaceWidth = dc.GetTextExtent(" ")[0]

    (rectX, rectY, rectWidth, rectHeight) = rect
    y = rectY
    rectRight = rectX + rectWidth
    rectBottom = rectY + rectHeight

    # we hit this if you narrow the main window enough:
    # assert rectHeight >= lineHeight, "Don't have enough room to write anything (have %d, need %d)" % (rectHeight, lineHeight)
    if rectHeight < lineHeight: return 0 # Can't draw anything

    for line in text.splitlines():
        x = rectX
        # accumulate text to be written on a line
        thisLine = u''
        for word in line.split():
            width = dc.GetTextExtent(word)[0]

            # if we wrapped but we still can't fit the word,
            # just truncate it
            if (width > rectWidth and x == rectX):
                assert thisLine == u'', "Should be drawing first long word"
                DrawClippedText(dc, word, rectX, y, rectWidth, width)
                y += lineHeight
                continue

            # see if we want to jump to the next line
            if (x + width > rectRight):
                # wrapping, so draw the previous accumulated line if any
                if thisLine:
                    dc.DrawText(thisLine, rectX, y)
                    thisLine = u''
                y += lineHeight
                x = rectX

            # if we're out of vertical space, just return
            if (y + lineHeight > rectBottom):
                assert thisLine == u'', "shouldn't have any more to draw"
                return
                #return y - rectY # total height

            availableWidth = rectRight - x
            if width > availableWidth:
                assert x == rectX and thisLine == u'', "should be writing a long word at the beginning of a line"
                DrawClippedText(dc, word, rectX, y, availableWidth, width)
                x += width
                # x is now past rectRight, so this will force a wrap
            else:
                # rather than draw it, just accumulate it
                thisLine += word + u' '
                x += width + spaceWidth

        # draw the last words on this line, if any
        if thisLine:
            dc.DrawText(thisLine, rectX, y)
        y += lineHeight
    #return y - rectY # total height


def DrawClippedText(dc, word, x, y, maxWidth, wordWidth = -1):
    """
    Draw the text, clipping at letter boundaries. This is optimized to
    reduce the number of calls to GetTextExtent by first estimating
    the length of the word that will fit in the given width.

    Note that I did consider some sort of complex quicksearch
    algorithm to find the right fit, but generally you're dealing with
    less than 20 or so characters at a time and you can actually guess
    reasonably accurately even with proportional fonts. This means its
    probably cheaper to just start walking up or down from the guess,
    rather than trying to do a quicksearch -alecf
    """
    x, y = round(x), round(y)
    if wordWidth < 0:
        # do some initial measurements
        wordWidth = dc.GetTextExtent(word)[0]

    # this is easy, so catch this early
    if wordWidth <= maxWidth:
        dc.DrawText(word, x, y)
        return

    # take a guess at how long the word should be
    testLength = int((maxWidth*100/wordWidth)*len(word)/100)
    wordWidth = dc.GetTextExtent(word[0:testLength])[0]

    # now check if the guessed length actually fits
    if wordWidth < maxWidth:
        # yep, it fit!
        # keep increasing word until it won't fit
        for newLen in range(testLength, len(word)+1, 1):
            wordWidth = dc.GetTextExtent(word[0:newLen])[0]
            if wordWidth > maxWidth:
                dc.DrawText(word[0:newLen-1], x, y)
                return
        #assert False, "Didn't draw any text!"
    else:
        # no, it didn't fit
        # keep shrinking word until it fits
        for newLen in range(testLength, 0, -1):
            wordWidth = dc.GetTextExtent(word[0:newLen])[0]
            if wordWidth <= maxWidth:
                dc.DrawText(word[0:newLen], x,y)
                return
        #assert False, "Didn't draw any text!"

class vector(list):

    def __add__(self, other):
        return vector(map(lambda x,y: x+y, self, other))

    def __neg__(self):
        return vector(map(lambda x: -x, self))

    def __sub__(self, other):
        return vector(map(lambda x,y: x-y, self, other))

    def __mul__(self, const):
        return vector(map(lambda x: x*const, self))
    
    def __rmul__(self, other):
            return (self*other)
        
    def join(self, other):
        return list.__add__(self, other)


class Gradients(object):
    """
    Gradient cache. 
    Creates and caches gradient bitmaps of size n x 1, going from one color
    to another. It does this by varying the HSV-based saturation so the
    assumption is that the incoming colors are of the same hue.
    
    Note that the brush also requires an offset, which is the offset from the
    VIEWPORT that the brush will be used. Thus if you'll be painting
    something whose left edge is really at x=100, you need to pass in 100
    for the offset. This is because wxWidgets does not have a(working) way
    to offset brushes on all 3 platforms.
    
    TODO: abstract this out to let the user choose left/right or top/bottom
    style gradient cache.
    """
    def __init__(self):
        self.ClearCache()
        self.hits = 0
        self.misses = 0
    
    def ClearCache(self):
        """
        Clears the gradient cache - used if you just don't need gradients of
        that particular width of height
        """
        self._gradientCache = {}
        self._dashCache  = {}
    
    def MakeGradientBrush(self, offset, bitmapWidth, leftColor, rightColor,
                          orientation):
        """
        Creates a gradient brush from leftColor to rightColor, specified
        as color tuples(r,g,b)
        The brush is a bitmap, width of self.dayWidth, height 1. The color 
        gradient is made by varying the color saturation from leftColor to 
        rightColor. This means that the Hue and Value should be the same, 
        or the resulting color on the right won't match rightColor
        """
        
        # There is probably a nicer way to do this, without:
        # - going through wxImage
        # - individually setting each RGB pixel
        
        #An image created with a negative widths will cause image.GetDataBuffer() to fail.
        assert bitmapWidth > 0
        if orientation == "Horizontal":
            image = wx.EmptyImage(bitmapWidth, 1)
        else:
            image = wx.EmptyImage(1, bitmapWidth)
        leftHSV = rgb_to_hsv(*color2rgb(*leftColor))
        rightHSV = rgb_to_hsv(*color2rgb(*rightColor))
        
        left  = vector(leftHSV)
        right = vector(rightHSV)
                
        if bitmapWidth == 0: bitmapWidth = 1
        step = (right - left) * (1.0 / bitmapWidth)
        
        # assign a sliding scale of floating point values from left to right
        # in the bitmap
        offset %= bitmapWidth

        bufferX = 0
        imageBuffer = image.GetDataBuffer()
        
        for x in xrange(bitmapWidth):
            
            # first offset the gradient within the bitmap
            # gradientIndex is the index of the color, i.e. the nth
            # color between leftColor and rightColor
            
            # First offset within the bitmap. The + bitmapWidth % bitmapWidth
            # ensures we're dealing with x<offset correctly
            gradientIndex = (x - offset + bitmapWidth) % bitmapWidth
            
            # now calculate the actual color from the gradient index
            hsvVector = left + step * gradientIndex
            color = rgb2color(*hsv_to_rgb(*hsvVector))

            # use the image buffer to write values directly
            # amazingly, this %c techinque to convert
            # is actually faster than either of:
            # chr(color[0]) + chr(color[1]) + chr(color[2])
            # ''.join(map(chr,color))
            imageBuffer[bufferX:bufferX+3] = pack('BBB', *color)

            bufferX += 3

        # and now we have to go from Image -> Bitmap. Yuck.
        brush = wx.Brush(wx.WHITE, wx.STIPPLE)
        brush.SetStipple(wx.BitmapFromImage(image))
        return brush

    def GetGradientBrush(self, offset, width, leftColor, rightColor,
                         orientation="Horizontal"):
        """
        Gets an appropriately sized gradient brush from the cache, 
        or creates one if necessary
        """
        assert orientation in ("Horizontal", "Vertical")
        key = (offset, width, leftColor, rightColor, orientation)
        if leftColor == rightColor:
            return wx.TheBrushList.FindOrCreateBrush(leftColor, wx.SOLID)
        brush = self._gradientCache.get(key, None)
        if brush is None:
            self.misses += 1
            brush = self.MakeGradientBrush(*key)
            self._gradientCache[key] = brush
        else:
            self.hits += 1
        return brush

    def MakeDash(self, offset, pattern, color, orientation):
        bitmapWidth = sum(pattern)
        if orientation == "Horizontal":
            image = wx.EmptyImage(bitmapWidth, 1)
        else:
            image = wx.EmptyImage(1, bitmapWidth)

        offset *= 3 # three color bytes per pixel
        colorAndWidth = izip(cycle([color, (255,255,255)]), pattern)

        bufferX = 0
        imageBuffer = image.GetDataBuffer()
        for col, width in colorAndWidth:
            newBufferX = bufferX + 3 * width
            imageBuffer[bufferX:newBufferX] = width * pack('BBB', *col)
            bufferX = newBufferX

        # shift the bytes by offset
        imageBuffer[:] = imageBuffer[offset:] + imageBuffer[:offset]
        brush = wx.Brush(wx.WHITE, wx.STIPPLE)
        brush.SetStipple(wx.BitmapFromImage(image))
        return brush

    def GetDash(self, offset, pattern, color, orientation):
        key = (offset % len(pattern), color, orientation)
        dash = self._dashCache.get(key, None)
        if dash is None:
            dash = self.MakeDash(offset, pattern, color, orientation)
            self._dashCache[key] = dash
        return dash

fontCache = {}

platformDefaultFaceName = None
platformDefaultFamily = None
platformSizeScalingFactor = 0.0

# "Fake" superscript (implemented in this file, wx doesn't seem to have any
# concept of super- or subscripting) is smaller, but its top is supposed to
# line up with non-fakesuperscript text.
#
# NB: unlike normal text, the CharacterStyle.fontSize will be different
# (bigger) than the post-scaling height reported by dc.GetTextExtent(), since wx
# fonts don't know about super/subscriptness.

fakeSuperscriptSizeScalingFactor = 0.7

# We default to an 11-point font, which gets scaled by the size of the
# platform's default GUI font (which we measured just above). It's 11
# because that's the size of the Mac's default GUI font, which is what
# Mimi thinks in terms of. (It's a float so the math works out.)
rawDefaultFontSize = 11.0

def getFont(characterStyle=None, family=None, size=rawDefaultFontSize, 
            style=wx.NORMAL, underline=False, weight=wx.NORMAL, name=""):
    """
    Retrieve a font, using a CharacterStyle item or discrete specifications.
    Scales the requested point size relative to the idealized 11-point size 
    on Mac that Mimi bases her specs on.
    """
    # Check the cache if we're using a style that we've used before
    if characterStyle is not None:
        key = getattr(characterStyle, 'fontKey', None)
        if key is not None:
            font = fontCache.get(key)
            if font is not None:
                return font
            
    # First time, get a couple of defaults
    global platformDefaultFaceName, platformDefaultFamily, platformSizeScalingFactor
    if platformDefaultFaceName is None:
        defaultGuiFont = wx.SystemSettings_GetFont(wx.SYS_DEFAULT_GUI_FONT)
        platformDefaultFaceName = defaultGuiFont.GetFaceName()
        platformDefaultFamily = defaultGuiFont.GetFamily()
        platformSizeScalingFactor = \
            defaultGuiFont.GetPointSize() / rawDefaultFontSize
        
    family = family or platformDefaultFamily
    
    if characterStyle is not None:
        size = characterStyle.fontSize
        name = characterStyle.fontName        

        if characterStyle.fontFamily == "SerifFont":
            family = wx.ROMAN
        elif characterStyle.fontFamily == "SanSerifFont":
            family = wx.SWISS
        elif characterStyle.fontFamily == "FixedPitchFont":
            family = wx.MODERN
                    
        for theStyle in characterStyle.fontStyle.split():
            lowerStyle = theStyle.lower()
            if lowerStyle == "bold":
                weight = wx.BOLD
            elif lowerStyle == "light":
                weight = wx.LIGHT
            elif lowerStyle == "italic":
                style = wx.ITALIC
            elif lowerStyle == "underline":
                underline = True
            elif lowerStyle == "fakesuperscript":
                size *= fakeSuperscriptSizeScalingFactor
        
    if family == platformDefaultFamily:
        name = platformDefaultFaceName

    # Scale the requested size by the platform's scaling factor (then round to int)
    scaledSize = int((platformSizeScalingFactor * size) + 0.5)
    
    # Do we have this already?
    key = (scaledSize, family, style, weight, underline)
    font = fontCache.get(key)
    if font is None:
        font = wx.Font(scaledSize, family, style, weight, underline, name)

        # Put the key in the font, as well as the characterStyle if we have one;
        # they'll let us shortcut the lookup process later.
        font.fontKey = key
        if characterStyle is not None:
            characterStyle.fontKey = key
        
        fontCache[key] = font

    return font


if __name__ == '__main__':
    
    # Test/example of DrawWrappedText
    
    class TestFrame(wx.Frame):
        def __init__(self, *args, **kwds):
            super(TestFrame, self).__init__(*args, **kwds)
            self.Bind(wx.EVT_PAINT, self.OnPaint)
            self.Bind(wx.EVT_SIZE, self.OnSize)
            
        def OnPaint(self, event):
            dc = wx.PaintDC(self)
            dc.Clear()
            
            padding = 20
            w, h = self.GetSize()
            r = wx.Rect(0, 0, w, h)
            r.Deflate(padding, padding)
            dc.DrawRectangle(*r)
            
            DrawWrappedText(dc, "Resize this window!\n\n  Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.",
                            r)
        
        def OnSize(self, event):
            self.Refresh(False)
    
        
    class TestApp(wx.App):
        def OnInit(self):
            frame = TestFrame(None, -1, "Test frame -- resize me!")
            frame.Show(True)
            self.SetTopWindow(frame)
            return True
     
    app = TestApp(0)
    app.MainLoop()
