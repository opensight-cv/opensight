import glob
import logging
import re
import subprocess
import time

import cv2
from   picamera import PiCamera
from   picamera.array import PiRGBArray

LOGGER = logging.getLogger(__name__)

__package__ = "opsi.input"

ENABLE_RES = False
ENABLE_FPS = False


def get_w(string):
    camstring = parse_camstring(string)
    if len(camstring) >= 3:
        camtuple = parse_camstring(string)
        return camtuple[1] + camtuple[2]
    return 0


def get_codec(v4l2_out):
    # for each codec, add the codec name and the description from v4l2-ctl (regex allowed), and FOURCC name
    # order by priority
    codecs = [
        ("H264", "H.264, compressed", "X264"),
        ("MJPG", "Motion-JPEG, compressed", "MJPG"),
        ("YUYV", r"YUYV \d:\d:\d", "YUYV"),
        ("YU12", r"Planar YUV \d:\d:\d", "YU12"),
    ]
    for i in codecs:
        # [digit] '<CODEC NAME>' (<CODEC DESCRIPTION>)
        # ex. [1]: 'MJPG' (Motion-JPEG, compressed)
        pattern1 = fr"\[\d+\]: '{i[0]}' \({i[1]}\) (.+)(\[\d+\].+)"
        lines1 = re.search(pattern1, v4l2_out)
        if lines1 is not None:
            return (cv2.VideoWriter_fourcc(*i[2]), lines1.group(1))
        pattern2 = fr"\[\d+\]: '{i[0]}' \({i[1]}\) (.+)($)"
        lines2 = re.search(pattern2, v4l2_out)
        if lines2 is not None:
            return (cv2.VideoWriter_fourcc(*i[2]), lines2.group(1))
    return None


def get_cam_info(cam):
    try:
        sp_out = subprocess.run(
            f"v4l2-ctl -d {str(cam)} --list-formats-ext".split(),
            capture_output=True,
            check=True,
        )
        return str(sp_out.stdout).replace("\\n", " ").replace("\\t", "")
    except subprocess.CalledProcessError:
        pass
    return None


def get_modes():
    # TODO: don't use globals, move all of this to a class and make a instance for module
    global ENABLE_FPS
    global ENABLE_RES

    all_modes = set()
    cam_list = (cam.replace("/dev/video", "") for cam in glob.glob("/dev/video*"))

    for cam in sorted(cam_list, key=int):

        caminfo = get_cam_info(cam)

        # remove cameras of these types
        # PiCam has extraneous cameras with type "Video Capture Multiplanar"

        skip = False
        cam_blacklist = ("Video Capture Multiplanar",)
        for i in cam_blacklist:
            if re.search(i, caminfo):
                skip = True
        if skip:
            continue

        codec = get_codec(caminfo)
        if codec is None:
            continue

        # group 1: resolution
        # group 2: everything up until next instance of Size
        any_set = False
        for match in re.finditer(r"Size: Discrete (\d+x\d+) ", codec[1]):
            resolution = match.group(1)
            # get everything from the curent resolution to the next resolution
            line = re.search(
                fr"{match.group(0)}(.+?)Size|{match.group(0)}(.+)", codec[1]
            )
            line = line.group(1) or line.group(2)
            fpses = set()
            for interval in re.finditer(r"nterval: \w+ \d+\.\d+s \((.+?) fps\)", line):
                fpses.add(float(interval.group(1)))
            # convert to float to use %g formatting, removing extraneous decimals
            if resolution:
                if fpses:
                    all_modes.add(
                        "Cam {0}: {1} @ {2:g} fps".format(
                            cam, resolution, float(max(fpses))
                        )
                    )
                    any_set = True
                else:
                    all_modes.add("Cam {0}: {1}".format(cam, resolution))
                    any_set = True
                    ENABLE_FPS = True
        if not any_set:
            all_modes.add("Cam {0}".format(cam))
            ENABLE_RES = True

    return tuple(sorted(all_modes, key=get_w, reverse=True))


def parse_camstring(string):
    camstring = []
    # group 3: any digit+ OR any digit+, decimal, any digit+
    m = re.search(r"(?:Cam (\d+))?(?::( \d+)x(\d+))?(?: @ (\d+|\d+.\d+) fps)?", string)
    cam = m.group(1)
    w = m.group(2)
    h = m.group(3)
    fps = m.group(4)
    if cam:
        camstring.append(int(cam))
    if w and h:
        camstring.append(int(w))
        camstring.append(int(h))
    if fps:
        camstring.append(float(fps))
    return tuple(camstring)


def controls(fps=False):
    if ENABLE_RES:
        return int
    if fps and ENABLE_FPS:
        return int
    return None


#def set_property(cap, prop, value):
#    try:
#        cap.set(prop, value)
#    except AttributeError:
#        LOGGER.debug("Camera does not support property %s", property)


def create_capture(settings):
    mode = parse_camstring(settings.mode)
    if len(mode) < 1:
        return None

    if len(mode) >= 3:
        w = mode[1]
        h = mode[2]
    else:
        w = settings.width
        h = settings.height

    if w < 320 or h < 240:
        w = 320
        h = 240
 
    if len(mode) >= 4:
        fps = mode[3]
    else:
        fps = settings.fps

    cap = PiCamera(mode[0])
    cap.resolution = (w,h)

    #####
    # brightness
    #   0..100 default 50
    # contrast
    #   -100..100 default is 0
    # drc_strength is dynamic range compression strength
    #   off, low, medium, high, default off
    # sharpness
    #   -100..100 default 0
    #####
    # iso
    #   0=auto, 100, 200, 320, 400, 500, 640, 800, on some cameras iso100 is gain of 1 and iso200 is gain of 2
    # exposure mode 
    #   off, auto, night, nightpreview, backight, spotlight, sports, snow, beach, verylong, fixedfps, antishake, fireworks, 
    #   default is auto, off fixes the analog and digital gains
    # exposure compensation
    #   -25..25, 
    #   larger value gives brighter images, default is 0
    # meter_mode
    #   'average', 'spot', 'backlit', 'matrix'
    #####
    # awb_mode
    #   off, auto, sunLight, cloudy, share, tungsten, fluorescent, flash, horizon, default is auto
    # analog gain
    #   retreives the analog gain prior to digitization
    # digital gain
    #   applied after conversion, a fraction
    # awb_gains
    #   0..8 for red,blue, typical values 0.9..1.9 if awb mode is set to "off
    #####
    # clock mode
    #   "reset", is relative to start of recording, "raw" is relative to start of camera
    # color_effects
    #   "None" or (u,v) where u and v are 0..255 e.g. (128,128) gives black and white image
    # flash_mode
    #   'off', 'auto', 'on', 'redeye', 'fillin', 'torch' defaults is off
    # image_denoise
    #   True or False, activates the denosing of the image
    # video_denoise
    #   True or False, activates the denosing of the video recording
    # image_effect
    #   negative, solarize, sketch, denoise, emboss, oilpaint, hatch, gpen, pastel, watercolor, film, 
    #   blur, saturation, colorswap, washedout, colorpoint, posterise, colorbalance, cartoon, deinterlace1, 
    #   deinterlace2, default is 'none'
    # image_effect_params
    #   setting the parameters for the image effects 
    #   see https://picamera.readthedocs.io/en/release-1.13/api_camera.html
    # video_stabilization
    #   default is False
    #####

    if settings.exposure > 0 :
        # Manual Settings, most feaures are off
        ##########################################################
        cap.framerate      = fps
        cap.brightness     = settings.brightness # No change in brightness
        cap.shutter_speed  = settings.exposure   # Sets exposure in microseconds, if 0 then autoexposure
        cap.awb_mode       = 'off'            # No auto white balance
        cap.awb_gains      = (1,1)            # Gains for red and blue are 1
        cap.contrast       = 0                # No change in contrast
        cap.drc_strength   = 'off'            # Dynamic Range Compression off
        cap.clock_mode     = 'raw'            # Frame numbers since opened capera
        cap.color_effects  = None             # No change in color
        cap.flash_mode     = 'off'            # No flash
        cap.image_denoise  = False            # In vidoe mode
        cap.image_effect   = 'none'           # No image effects
        cap.sharpness      = 0                # No changes in sharpness
        cap.video_stabilization = False       # No image stablization
        cap.exposure_mode  = 'off'            # No automatic exposure control
        cap.exposure_compensation = 0         # No automatic expsoure controls compensation
    else:
        # Auto Exposure and Auto White Balance
        ############################################################
        cap.framerate      = fps
        cap.brightness     = settings.brightness # No change in brightness
        cap.shutter_speed  = 0                # Sets exposure in microseconds, if 0 then autoexposure
        cap.iso            = 0                # Auto ISO
        cap.awb_mode       = 'on'             # No auto white balance
        cap.awb_gains      = (1,1)            # Gains for red and blue are 1
        cap.contrast       = 0                # No change in contrast
        cap.drc_strength   = 'off'            # Dynamic Range Compression off
        cap.clock_mode     = 'raw'            # Frame numbers since opened capera
        cap.color_effects  = None             # No change in color
        cap.flash_mode     = 'off'            # No flash
        cap.image_denoise  = False            # In vidoe mode
        cap.image_effect   = 'none'           # No image effects
        cap.sharpness      = 0                # No changes in sharpness
        cap.video_stabilization = False       # No image stablization
        cap.exposure_mode  = 'on'             # automatic exposure control
        cap.exposure_compensation = 0         # No automatic expsoure controls compensation

    capBuffer = PiRGBArray(cap)

    return cap, capBuffer