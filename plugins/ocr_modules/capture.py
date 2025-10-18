# plugins/ocr_modules/capture.py
import mss
from PIL import Image
import win32gui
import win32ui
import win32con
from enum import Enum

class CaptureMethod(Enum):
    AUTODETECT = "auto"
    BITBLT = "bitblt"
    PRINTWINDOW = "printwindow"
    PRINTWINDOW_FULL = "printwindow_full"  # PW_RENDERFULLCONTENT
    MSS = "mss"

class WindowCapture:
    def __init__(self):
        self.current_method = CaptureMethod.AUTODETECT
        self.available_methods = list(CaptureMethod)
    
    def set_method(self, method):
        """Set the capture method for a region"""
        if isinstance(method, str):
            method = CaptureMethod(method)
        self.current_method = method
    
    def capture_region(self, hwnd=None, region=None, subregion_bounds=None):
        """
        Capture a window or screen region with optional subregion
        
        Args:
            hwnd: Window handle (for window capture)
            region: dict with 'left', 'top', 'width', 'height' (for screen capture)
            subregion_bounds: tuple (x, y, width, height) relative to window for subregion capture
        """
        if hwnd and subregion_bounds:
            return self._capture_window_subregion(hwnd, subregion_bounds)
        elif hwnd:
            return self._capture_window(hwnd)
        elif region:
            return self._capture_screen_region(region)
        else:
            raise ValueError("Either hwnd or region must be provided")

    def _capture_window_subregion(self, hwnd, subregion_bounds):
        """Capture a subregion of a window using window capture methods"""
        # First capture the entire window
        full_window_image = self._capture_window(hwnd)

        if not full_window_image:
            return None

        # Extract subregion coordinates
        sub_x, sub_y, sub_w, sub_h = subregion_bounds

        # Ensure subregion is within window bounds
        if (sub_x < 0 or sub_y < 0 or 
            sub_x + sub_w > full_window_image.width or 
            sub_y + sub_h > full_window_image.height):
            print(f"Warning: Subregion {subregion_bounds} outside window bounds {full_window_image.size}")
            # Clamp to window bounds
            sub_x = max(0, sub_x)
            sub_y = max(0, sub_y)
            sub_w = min(sub_w, full_window_image.width - sub_x)
            sub_h = min(sub_h, full_window_image.height - sub_y)
    
        # Crop to subregion
        subregion_image = full_window_image.crop((sub_x, sub_y, sub_x + sub_w, sub_y + sub_h))
        return subregion_image    
    
    def _capture_window(self, hwnd):
        """Capture window using selected method"""
        if self.current_method == CaptureMethod.AUTODETECT:
            return self._capture_window_auto(hwnd)
        elif self.current_method == CaptureMethod.BITBLT:
            return self._capture_window_bitblt(hwnd)
        elif self.current_method == CaptureMethod.PRINTWINDOW:
            return self._capture_window_printwindow(hwnd, flags=0)
        elif self.current_method == CaptureMethod.PRINTWINDOW_FULL:
            return self._capture_window_printwindow(hwnd, flags=2)
        elif self.current_method == CaptureMethod.MSS:
            return self._capture_window_mss(hwnd)
    
    def _capture_window_auto(self, hwnd):
        """Auto-detect best method for window"""
        methods_to_try = [
            (CaptureMethod.PRINTWINDOW_FULL, lambda: self._capture_window_printwindow(hwnd, 2)),
            (CaptureMethod.PRINTWINDOW, lambda: self._capture_window_printwindow(hwnd, 0)),
            (CaptureMethod.BITBLT, lambda: self._capture_window_bitblt(hwnd)),
            (CaptureMethod.MSS, lambda: self._capture_window_mss(hwnd)),
        ]
        
        for method_name, capture_func in methods_to_try:
            try:
                result = capture_func()
                print(f"Auto-selected method: {method_name.value}")
                return result
            except Exception as e:
                print(f"Method {method_name.value} failed: {e}")
                continue
        
        raise Exception("All capture methods failed")
    
    def _capture_window_bitblt(self, hwnd):
        """Traditional BitBlt method"""
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        width = right - left
        height = bottom - top
        
        hwndDC = win32gui.GetWindowDC(hwnd)
        mfcDC = win32ui.CreateDCFromHandle(hwndDC)
        saveDC = mfcDC.CreateCompatibleDC()
        
        saveBitMap = win32ui.CreateBitmap()
        saveBitMap.CreateCompatibleBitmap(mfcDC, width, height)
        saveDC.SelectObject(saveBitMap)
        
        # Use BitBlt
        saveDC.BitBlt((0, 0), (width, height), mfcDC, (0, 0), win32con.SRCCOPY)
        
        bmpinfo = saveBitMap.GetInfo()
        bmpstr = saveBitMap.GetBitmapBits(True)
        
        im = Image.frombuffer(
            'RGB',
            (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
            bmpstr, 'raw', 'BGRX', 0, 1
        )
        
        # Clean up
        win32gui.DeleteObject(saveBitMap.GetHandle())
        saveDC.DeleteDC()
        mfcDC.DeleteDC()
        win32gui.ReleaseDC(hwnd, hwndDC)
        
        return im
    
    def _capture_window_printwindow(self, hwnd, flags=0):
        """PrintWindow method with configurable flags"""
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        width = right - left
        height = bottom - top
        
        hwndDC = win32gui.GetWindowDC(hwnd)
        mfcDC = win32ui.CreateDCFromHandle(hwndDC)
        saveDC = mfcDC.CreateCompatibleDC()
        
        saveBitMap = win32ui.CreateBitmap()
        saveBitMap.CreateCompatibleBitmap(mfcDC, width, height)
        saveDC.SelectObject(saveBitMap)
        
        # Use PrintWindow with flags
        result = win32gui.PrintWindow(hwnd, saveDC.GetSafeHdc(), flags)
        
        if result != 1:
            raise Exception(f"PrintWindow failed with result: {result}")
        
        bmpinfo = saveBitMap.GetInfo()
        bmpstr = saveBitMap.GetBitmapBits(True)
        im = Image.frombuffer(
            'RGB',
            (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
            bmpstr, 'raw', 'BGRX', 0, 1
        )
        
        # Clean up
        win32gui.DeleteObject(saveBitMap.GetHandle())
        saveDC.DeleteDC()
        mfcDC.DeleteDC()
        win32gui.ReleaseDC(hwnd, hwndDC)
        
        return im
    
    def _capture_window_mss(self, hwnd):
        """MSS method for window capture"""
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        monitor = {
            "left": left,
            "top": top, 
            "width": right - left,
            "height": bottom - top
        }
        
        with mss.mss() as sct:
            sct_img = sct.grab(monitor)
            return Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
    
    def _capture_screen_region(self, region):
        """Capture screen region (for non-window areas)"""
        if self.current_method == CaptureMethod.MSS:
            with mss.mss() as sct:
                sct_img = sct.grab(region)
                return Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
        else:
            # Fallback to BitBlt for screen regions
            hwnd = win32gui.GetDesktopWindow()
            left, top, width, height = region['left'], region['top'], region['width'], region['height']
            
            hwndDC = win32gui.GetWindowDC(hwnd)
            mfcDC = win32ui.CreateDCFromHandle(hwndDC)
            saveDC = mfcDC.CreateCompatibleDC()
            
            saveBitMap = win32ui.CreateBitmap()
            saveBitMap.CreateCompatibleBitmap(mfcDC, width, height)
            saveDC.SelectObject(saveBitMap)
            
            saveDC.BitBlt((0, 0), (width, height), mfcDC, (left, top), win32con.SRCCOPY)
            
            bmpinfo = saveBitMap.GetInfo()
            bmpstr = saveBitMap.GetBitmapBits(True)
            
            im = Image.frombuffer(
                'RGB',
                (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
                bmpstr, 'raw', 'BGRX', 0, 1
            )
            
            # Clean up
            win32gui.DeleteObject(saveBitMap.GetHandle())
            saveDC.DeleteDC()
            mfcDC.DeleteDC()
            win32gui.ReleaseDC(hwnd, hwndDC)
            
            return im
