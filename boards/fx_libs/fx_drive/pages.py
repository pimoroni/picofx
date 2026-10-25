# The packed pages fx_editor and fx_manual carry, and how each is written onto the drive

import binascii
import deflate
import io

import fx_editor
import fx_manual

MANUAL_NAME = "MANUAL.html"
PICKER_NAME = "PICKER.html"
EDITOR_NAME = "EDITOR.html"
CATALOGUE_NAME = "catalogue.js"

# How much of a packed page is inflated onto the drive at a time
__INFLATE_CHUNK = 4096


def __inflate(packed, f):
    # Write a zlib stream to the open file, a chunk at a time
    # BytesIO reads a frozen bytes object in place, where a read() of the whole
    # stream would put the page on the heap
    stream = deflate.DeflateIO(io.BytesIO(packed), deflate.ZLIB)
    chunk = bytearray(__INFLATE_CHUNK)
    while True:
        count = stream.readinto(chunk)
        if not count:
            return
        f.write(memoryview(chunk)[:count])


def __encode(packed, f):
    # Write a zlib stream to the open file as base64, a chunk at a time
    # A multiple of three bytes encodes without padding, so the chunks join up
    step = __INFLATE_CHUNK // 4 * 3
    view = memoryview(packed)
    for at in range(0, len(packed), step):
        f.write(binascii.b2a_base64(view[at:at + step], newline=False))


def pages(screens):
    """
    Each packed page's name on the drive and its document, the catalogue without the
    screens for a board found to have no screen ports.
    """
    catalogue = fx_editor.CATALOGUE
    if not screens:
        catalogue = getattr(fx_editor, "CATALOGUE_WITHOUT_SCREENS", catalogue)
    return ((MANUAL_NAME, fx_manual.MANUAL), (PICKER_NAME, fx_editor.PICKER),
            (EDITOR_NAME, fx_editor.EDITOR), (CATALOGUE_NAME, catalogue))


def write_page(document, f):
    """
    Write a packed page to the open file. A page that inflates itself in the browser
    carries its opening and closing, and its stream goes between them in base64.
    """
    if len(document) == 6:
        _, _, _, packed, opening, closing = document
        f.write(opening)
        __encode(packed, f)
        f.write(closing)
    else:
        __inflate(document[3], f)
