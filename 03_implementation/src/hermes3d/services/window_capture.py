"""Windows desktop window discovery, capture, and local input bridge."""

from __future__ import annotations

import io
import time
from ctypes import windll
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from PIL import Image

try:  # pragma: no cover - exercised on Windows desktop runtime
    import win32api
    import win32con
    import win32gui
    import win32process
    import win32ui
except ImportError:  # pragma: no cover - non-Windows fallback
    win32api = None
    win32con = None
    win32gui = None
    win32process = None
    win32ui = None


@dataclass(frozen=True)
class DesktopWindow:
    hwnd: int
    title: str
    process_id: int
    process_path: str
    process_name: str
    rect: tuple[int, int, int, int]
    is_minimized: bool


def windows_available() -> bool:
    return all((win32api, win32con, win32gui, win32process, win32ui))


def list_desktop_windows() -> list[DesktopWindow]:
    if not windows_available():
        return []
    result: list[DesktopWindow] = []

    def _callback(hwnd: int, _extra: object) -> bool:
        if not win32gui.IsWindowVisible(hwnd):
            return True
        title = win32gui.GetWindowText(hwnd).strip()
        if not title:
            return True
        rect = tuple(int(item) for item in win32gui.GetWindowRect(hwnd))
        width = rect[2] - rect[0]
        height = rect[3] - rect[1]
        if width <= 0 or height <= 0:
            return True
        _thread_id, pid = win32process.GetWindowThreadProcessId(hwnd)
        process_path = _process_path(pid)
        result.append(
            DesktopWindow(
                hwnd=int(hwnd),
                title=title,
                process_id=int(pid),
                process_path=process_path,
                process_name=Path(process_path).stem if process_path else "",
                rect=rect,
                is_minimized=bool(win32gui.IsIconic(hwnd)),
            )
        )
        return True

    win32gui.EnumWindows(_callback, None)
    return result


def list_matching_windows(
    *,
    process_names: Iterable[str] = (),
    title_contains: Iterable[str] = (),
    executable_path: str | None = None,
) -> list[DesktopWindow]:
    wanted_processes = {item.lower().removesuffix(".exe") for item in process_names if item}
    wanted_titles = [item.lower() for item in title_contains if item]
    wanted_path = str(Path(executable_path)).lower() if executable_path else ""
    matches: list[DesktopWindow] = []
    for item in list_desktop_windows():
        process_name = item.process_name.lower().removesuffix(".exe")
        title = item.title.lower()
        path = item.process_path.lower()
        if wanted_path and path and Path(path) == Path(wanted_path):
            matches.append(item)
            continue
        if wanted_processes and process_name in wanted_processes:
            matches.append(item)
            continue
        if wanted_titles and all(part in title for part in wanted_titles):
            matches.append(item)
    return matches


def find_desktop_window(
    *,
    process_names: Iterable[str] = (),
    title_contains: Iterable[str] = (),
    executable_path: str | None = None,
) -> DesktopWindow | None:
    wanted_processes = {item.lower().removesuffix(".exe") for item in process_names if item}
    wanted_titles = [item.lower() for item in title_contains if item]
    wanted_path = str(Path(executable_path)).lower() if executable_path else ""
    matches: list[tuple[int, int, DesktopWindow]] = []
    for item in list_matching_windows(
        process_names=process_names,
        title_contains=title_contains,
        executable_path=executable_path,
    ):
        process_name = item.process_name.lower().removesuffix(".exe")
        title = item.title.lower()
        path = item.process_path.lower()
        area = max(0, item.rect[2] - item.rect[0]) * max(0, item.rect[3] - item.rect[1])
        capture_bonus = 0 if item.is_minimized else 10_000_000
        if wanted_path and path and Path(path) == Path(wanted_path):
            matches.append((3, capture_bonus + area, item))
            continue
        if wanted_processes and process_name in wanted_processes:
            matches.append((2, capture_bonus + area, item))
            continue
        if wanted_titles and all(part in title for part in wanted_titles):
            matches.append((1, capture_bonus + area, item))
    if not matches:
        return None
    return sorted(matches, key=lambda item: (item[0], item[1]), reverse=True)[0][2]


def capture_window_image(window: DesktopWindow, *, max_width: int | None = None) -> Image.Image:
    if not windows_available():
        raise RuntimeError("Windows desktop capture libraries are unavailable.")
    hwnd = int(window.hwnd)
    if win32gui.IsIconic(hwnd):
        focus_window(window)
    _move_parked_window(hwnd)
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    width = max(1, int(right - left))
    height = max(1, int(bottom - top))
    hwnd_dc = win32gui.GetWindowDC(hwnd)
    mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
    save_dc = mfc_dc.CreateCompatibleDC()
    bitmap = win32ui.CreateBitmap()
    bitmap.CreateCompatibleBitmap(mfc_dc, width, height)
    save_dc.SelectObject(bitmap)
    try:
        printed = windll.user32.PrintWindow(hwnd, save_dc.GetSafeHdc(), 2)
        if not printed:
            save_dc.BitBlt((0, 0), (width, height), mfc_dc, (0, 0), win32con.SRCCOPY)
        info = bitmap.GetInfo()
        data = bitmap.GetBitmapBits(True)
        image = Image.frombuffer(
            "RGB",
            (int(info["bmWidth"]), int(info["bmHeight"])),
            data,
            "raw",
            "BGRX",
            0,
            1,
        ).copy()
        if max_width and image.width > max_width:
            scale = max_width / max(1, image.width)
            image = image.resize((max_width, max(1, int(image.height * scale))), Image.Resampling.BILINEAR)
        return image
    finally:
        win32gui.DeleteObject(bitmap.GetHandle())
        save_dc.DeleteDC()
        mfc_dc.DeleteDC()
        win32gui.ReleaseDC(hwnd, hwnd_dc)


def capture_window_png(window: DesktopWindow) -> bytes:
    image = capture_window_image(window)
    out = io.BytesIO()
    image.save(out, format="PNG")
    return out.getvalue()


def capture_window_jpeg(window: DesktopWindow, *, quality: int = 72, max_width: int | None = 1600) -> bytes:
    image = capture_window_image(window, max_width=max_width)
    out = io.BytesIO()
    image.save(out, format="JPEG", quality=max(35, min(92, int(quality))), optimize=False)
    return out.getvalue()


def focus_window(window: DesktopWindow) -> None:
    if not windows_available():
        return
    hwnd = int(window.hwnd)
    if win32gui.IsIconic(hwnd):
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    _move_parked_window(hwnd)
    try:
        win32gui.SetForegroundWindow(hwnd)
    except Exception:
        try:
            win32gui.BringWindowToTop(hwnd)
            win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
        except Exception:
            pass


def click_window(window: DesktopWindow, *, x_ratio: float, y_ratio: float, button: str = "left", double: bool = False) -> None:
    if not windows_available():
        raise RuntimeError("Windows desktop input libraries are unavailable.")
    hwnd = int(window.hwnd)
    if win32gui.IsIconic(hwnd):
        raise RuntimeError("Window is minimized. Restore or focus it before sending input.")
    screen_x, screen_y = _window_screen_point(hwnd, x_ratio=x_ratio, y_ratio=y_ratio)
    client_x, client_y = win32gui.ScreenToClient(hwnd, (screen_x, screen_y))
    lparam = _make_lparam(client_x, client_y)
    down, up, key_flag = _mouse_messages(button)
    repeat = 2 if double else 1
    for _index in range(repeat):
        win32gui.PostMessage(hwnd, win32con.WM_MOUSEMOVE, 0, lparam)
        win32gui.PostMessage(hwnd, down, key_flag, lparam)
        time.sleep(0.03)
        win32gui.PostMessage(hwnd, up, 0, lparam)
        time.sleep(0.06)


def wheel_window(window: DesktopWindow, *, x_ratio: float, y_ratio: float, delta_y: float) -> None:
    if not windows_available():
        raise RuntimeError("Windows desktop input libraries are unavailable.")
    hwnd = int(window.hwnd)
    if win32gui.IsIconic(hwnd):
        raise RuntimeError("Window is minimized. Restore or focus it before sending input.")
    x, y = _window_screen_point(hwnd, x_ratio=x_ratio, y_ratio=y_ratio)
    wheel = -120 if delta_y > 0 else 120
    win32gui.PostMessage(hwnd, win32con.WM_MOUSEWHEEL, (wheel & 0xFFFF) << 16, _make_lparam(x, y))


def press_window_key(window: DesktopWindow, *, key: str, ctrl: bool = False, alt: bool = False, shift: bool = False) -> None:
    if not windows_available():
        raise RuntimeError("Windows desktop input libraries are unavailable.")
    hwnd = int(window.hwnd)
    if win32gui.IsIconic(hwnd):
        raise RuntimeError("Window is minimized. Restore or focus it before sending input.")
    modifiers: list[int] = []
    if ctrl:
        modifiers.append(win32con.VK_CONTROL)
    if alt:
        modifiers.append(win32con.VK_MENU)
    if shift:
        modifiers.append(win32con.VK_SHIFT)
    vk, implicit_shift = _virtual_key(key)
    if implicit_shift and win32con.VK_SHIFT not in modifiers:
        modifiers.append(win32con.VK_SHIFT)
    for mod in modifiers:
        win32gui.PostMessage(hwnd, win32con.WM_KEYDOWN, mod, 0)
    win32gui.PostMessage(hwnd, win32con.WM_KEYDOWN, vk, 0)
    if len(key) == 1 and not ctrl and not alt:
        win32gui.PostMessage(hwnd, win32con.WM_CHAR, ord(key), 0)
    time.sleep(0.02)
    win32gui.PostMessage(hwnd, win32con.WM_KEYUP, vk, 0)
    for mod in reversed(modifiers):
        win32gui.PostMessage(hwnd, win32con.WM_KEYUP, mod, 0)


def _move_parked_window(hwnd: int) -> None:
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    width = int(right - left)
    height = int(bottom - top)
    if width <= 0 or height <= 0:
        return
    if left < -10_000 or top < -10_000:
        win32gui.SetWindowPos(
            hwnd,
            None,
            80,
            80,
            max(width, 900),
            max(height, 700),
            win32con.SWP_NOZORDER | win32con.SWP_SHOWWINDOW,
        )


def _clamp_ratio(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _mouse_messages(button: str) -> tuple[int, int, int]:
    normalized = button.lower()
    if normalized == "right":
        return win32con.WM_RBUTTONDOWN, win32con.WM_RBUTTONUP, win32con.MK_RBUTTON
    if normalized == "middle":
        return win32con.WM_MBUTTONDOWN, win32con.WM_MBUTTONUP, win32con.MK_MBUTTON
    return win32con.WM_LBUTTONDOWN, win32con.WM_LBUTTONUP, win32con.MK_LBUTTON


def _window_screen_point(hwnd: int, *, x_ratio: float, y_ratio: float) -> tuple[int, int]:
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    width = max(1, int(right - left))
    height = max(1, int(bottom - top))
    return (
        int(left + _clamp_ratio(x_ratio) * width),
        int(top + _clamp_ratio(y_ratio) * height),
    )


def _make_lparam(x: int, y: int) -> int:
    return (int(y) & 0xFFFF) << 16 | (int(x) & 0xFFFF)


def _virtual_key(key: str) -> tuple[int, bool]:
    named = {
        "Enter": win32con.VK_RETURN,
        "Escape": win32con.VK_ESCAPE,
        "Backspace": win32con.VK_BACK,
        "Delete": win32con.VK_DELETE,
        "Tab": win32con.VK_TAB,
        "ArrowLeft": win32con.VK_LEFT,
        "ArrowRight": win32con.VK_RIGHT,
        "ArrowUp": win32con.VK_UP,
        "ArrowDown": win32con.VK_DOWN,
        "Home": win32con.VK_HOME,
        "End": win32con.VK_END,
        "PageUp": win32con.VK_PRIOR,
        "PageDown": win32con.VK_NEXT,
        " ": win32con.VK_SPACE,
    }
    if key in named:
        return named[key], False
    if len(key) == 1:
        code = win32api.VkKeyScan(key)
        if code == -1:
            raise RuntimeError(f"Unsupported key: {key!r}")
        vk = code & 0xFF
        shift = bool(code & 0x0100)
        return vk, shift
    if len(key) == 2 and key.upper().startswith("F") and key[1].isdigit():
        return win32con.VK_F1 + int(key[1]) - 1, False
    raise RuntimeError(f"Unsupported key: {key!r}")


def _process_path(pid: int) -> str:
    if not windows_available():
        return ""
    handle = None
    try:
        handle = win32api.OpenProcess(
            win32con.PROCESS_QUERY_INFORMATION | win32con.PROCESS_VM_READ,
            False,
            int(pid),
        )
        return str(win32process.GetModuleFileNameEx(handle, 0))
    except Exception:
        return ""
    finally:
        if handle:
            win32api.CloseHandle(handle)
