
import ctypes

def disable_quick_edit():
    """禁用控制台的快速编辑模式，防止程序假死"""
    try:
        # 定义Windows API常量
        ENABLE_QUICK_EDIT_MODE = 0x0040
        ENABLE_EXTENDED_FLAGS = 0x0080
        STD_INPUT_HANDLE = -10

        # 获取控制台句柄
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(STD_INPUT_HANDLE)
        
        # 获取当前控制台模式
        mode = ctypes.c_ulong()
        kernel32.GetConsoleMode(handle, ctypes.byref(mode))
        
        # 清除快速编辑模式位
        mode.value &= ~ENABLE_QUICK_EDIT_MODE
        # 设置扩展标志位
        mode.value |= ENABLE_EXTENDED_FLAGS
        
        # 设置新的控制台模式
        kernel32.SetConsoleMode(handle, mode)
        print("[Car_Park] 已禁用控制台快速编辑模式")
        
    except Exception as e:
        print(f"[Car_Park] 禁用快速编辑模式失败: {str(e)}")

# 程序启动时禁用快速编辑模式
disable_quick_edit()
