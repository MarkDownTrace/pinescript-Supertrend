import tkinter as tk
from datetime import datetime
import pytz

# 创建主窗口
window = tk.Tk()
window.title("时钟")
window.geometry("300x150")

# 创建标签用于显示时间和日期
time_label = tk.Label(window, font=("Helvetica", 36))
time_label.pack(pady=20)

date_label = tk.Label(window, font=("Helvetica", 18))
date_label.pack()

# 更新时间和日期
def update_time():
    # 获取当前时间和日期
    current_time = datetime.now().strftime("%H:%M:%S")
    current_date = datetime.now().strftime("%Y-%m-%d")

    # 显示当前时间和日期
    time_label.config(text=current_time)
    date_label.config(text=current_date)

    # 每隔1秒更新一次
    window.after(1000, update_time)

# 获取并显示特定时区的时间
def show_time_in_timezone():
    timezone = timezone_entry.get()

    try:
        # 获取特定时区的当前时间
        tz = pytz.timezone(timezone)
        current_time = datetime.now(tz).strftime("%H:%M:%S")

        # 显示特定时区的当前时间
        timezone_label.config(text="时间（{}）：{}".format(timezone, current_time))
    except pytz.UnknownTimeZoneError:
        timezone_label.config(text="无效的时区")

# 创建输入框和按钮用于调整时区
timezone_entry = tk.Entry(window, font=("Helvetica", 12))
timezone_entry.pack(pady=10)

show_time_button = tk.Button(window, text="显示特定时区时间", command=show_time_in_timezone)
show_time_button.pack()

timezone_label = tk.Label(window, font=("Helvetica", 12))
timezone_label.pack()

# 启动时钟
update_time()

# 运行主循环
window.mainloop()
