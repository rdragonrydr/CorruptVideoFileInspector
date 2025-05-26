#!/usr/bin/python3

import csv
import os
import subprocess
import tkinter as tk
import shlex
import platform
import psutil
import signal
import time
from threading import Thread
from tkinter import filedialog
from tkinter import ttk
try:
    from tkmacosx import Button
except ImportError:
    from tkinter import Button
from datetime import datetime

VIDEO_EXTENSIONS = ['.mp4', '.avi', '.mov', '.wmv', '.mkv', '.flv', '.webm', '.m4v', '.m4p', '.mpeg', '.mpg', '.3gp', '.3g2']

# ========================== CLASSES ===========================

class VideoObject():
    def __init__(self, filename, full_filepath):
        self.filename = filename
        self.full_filepath = full_filepath

# ========================= FUNCTIONS ==========================

def omniLog(msg, log_file):
    if log_file:
        log_file.write(msg)
        log_file.flush()
    print(msg)
    

def isMacOs():
    if 'Darwin' in platform.system():
        return True
    return False

def isWindowsOs():
    if 'Windows' in platform.system():
        return True
    return False

def isLinuxOs():
    if 'Linux' in platform.system():
        return True
    return False

def selectDirectory(root, label_select_directory, button_select_directory):
    # root.withdraw()
    directory = filedialog.askdirectory()

    if len(directory) > 0:
        label_select_directory.destroy()
        button_select_directory.destroy()
        afterDirectoryChosen(root, directory)


def convertTime(seconds):
    seconds = seconds % (24 * 3600)
    hour = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60
    return "%d:%02d:%02d" % (hour, minutes, seconds)

def truncateFilename(input):
    file_name, file_extension = os.path.splitext(input)
    if isLinuxOs() and len(file_name) > 49:
        truncated_string = file_name[0:48]
        return f'{truncated_string}..{file_extension}'
    elif isMacOs() and len(file_name) > 50:
        truncated_string = file_name[0:49]
        return f'{truncated_string}..{file_extension}'
    elif isWindowsOs() and len(file_name) > 42:
        truncated_string = file_name[0:41]
        return f'{truncated_string}..{file_extension}'
    else:
        return input

def countAllVideoFiles(dir):
    total = 0
    for root, dirs, files in os.walk(dir):
        for file in files:
            if file.lower().endswith(tuple(VIDEO_EXTENSIONS)):
                total += 1
    return total

def getAllVideoFiles(dir):
    videos_found_list = []
    for root, dirs, files in os.walk(dir):
        for file in files:
            if file.lower().endswith(tuple(VIDEO_EXTENSIONS)):
                videos_found_list.append(file)
    videos_found_list.sort()
    index = 1
    sorted_videos_list = []
    for video in videos_found_list:
        sorted_videos_list.append(f' {index}:  {video}')
        index += 1
    return sorted_videos_list

def windowsFfmpegCpuCalculationPrimer():
    # https://psutil.readthedocs.io/en/latest/#psutil.cpu_percent
    # https://stackoverflow.com/questions/24367424/cpu-percentinterval-none-always-returns-0-regardless-of-interval-value-python
    process_names = [proc for proc in psutil.process_iter()]
    for proc in process_names:
        if "ffmpeg" in proc.name():
            cpu_usage = proc.cpu_percent()

def verify_ffmpeg_still_running(root):
    ffmpeg_window = tk.Toplevel(root)
    ffmpeg_window.resizable(False, False)
    ffmpeg_window.geometry("400x150")
    ffmpeg_window.title("Verify ffmpeg Status")
    output = ''
    cpu_usage = ''

    if isLinuxOs():
        proc = subprocess.Popen("ps -Ao comm,pcpu | grep ffmpeg", shell=True, stdout=subprocess.PIPE)
        output = proc.communicate()[0].decode('utf-8').strip()
        if "ffmpeg" in output:
            cpu_usage = output.split()[1]
            output = f"ffmpeg is currently running.\nffmpeg is currently using {cpu_usage}% of CPU"
        else:
            output = "ffmpeg is NOT currently running!"
    elif isMacOs():
        proc = subprocess.Popen("ps -Ao comm,pcpu -r | head -n 10 | grep ffmpeg", shell=True, stdout=subprocess.PIPE)
        output = proc.communicate()[0].decode('utf-8').strip()
        if "ffmpeg" in output:
            cpu_usage = output.split()[1]
            output = f"ffmpeg is currently running.\nffmpeg is currently using {cpu_usage}% of CPU"
        else:
            output = "ffmpeg is NOT currently running!"
    elif isWindowsOs():
        windowsFfmpegCpuCalculationPrimer()
        found = False
        process_names = [proc for proc in psutil.process_iter()]
        for proc in process_names:
            if "ffmpeg" in proc.name():
                cpu_usage = proc.cpu_percent()
                found = True
                break
        if found:
            output = f"ffmpeg is currently running.\nffmpeg is currently using {cpu_usage}% of CPU"
        else:
            output = "ffmpeg is NOT currently running!"
    else:
        output = "Your system is unknown,\nso it's not possible to tell if ffmpeg is running.\nConsider submitting a patch?"
    label_ffmpeg_result = tk.Label(ffmpeg_window, width=375, text=output, font=('Helvetica', 14))
    label_ffmpeg_result.pack(fill=tk.X, pady=20)

def kill_ffmpeg_warning(root):
    global g_force_cancel_thread
    if not g_force_cancel_thread:
        ffmpeg_kill_window = tk.Toplevel(root)
        ffmpeg_kill_window.resizable(False, False)
        if isMacOs():
            ffmpeg_kill_window.geometry("400x300")
        else:
            ffmpeg_kill_window.geometry("400x400")
        ffmpeg_kill_window.title("Safely Quit Program")

        label_ffmpeg_kill = tk.Label(ffmpeg_kill_window, wraplength=375, width=375, text="This application spawns a subprocess named 'ffmpeg'. If this program is quit using the 'X' button, for example, the 'ffmpeg' subprocess will continue to run in the background of the host computer, draining the CPU resources. Clicking the button below will terminate the 'ffmpeg' subprocess and safely quit the application. This will prematurely end all video processing. Only do this if you want to safely exit the program and clean all subprocesses", font=('Helvetica', 14))
        label_ffmpeg_kill.pack(fill=tk.X, pady=20)

        if isMacOs(): only difference is mac has 'borderless'
            # https://stackoverflow.com/questions/1529847/how-to-change-the-foreground-or-background-colour-of-a-tkinter-button-on-mac-os
            button_kill_ffmpeg = Button(ffmpeg_kill_window, background='#E34234', borderless=1, foreground='white', text="Terminate Program", width=500, command=lambda: kill_ffmpeg(root))
        else: #Windows or Linux - the custom button fields don't exist, create the button without them
            button_kill_ffmpeg = Button(ffmpeg_kill_window, background='#E34234', foreground='white', text="Terminate Program", width=200, command=lambda: kill_ffmpeg(root))
        button_kill_ffmpeg.pack(pady=10)
    else:
        kill_ffmpeg(root)

def kill_ffmpeg(root):
    global log_file
    global g_force_cancel_thread
    g_force_cancel_thread = True
    try:
        omniLog(f'---USER MANUALLY TERMINATED PROGRAM---\n',log_file)
        if isLinuxOs():
            global g_lin_pid
            os.killpg(os.getpgid(g_lin_pid), signal.SIGTERM)
        elif isMacOs():
            global g_mac_pid
            os.killpg(os.getpgid(g_mac_pid), signal.SIGTERM)
        elif isWindowsOs():
            global g_windows_pid
            # os.kill(g_windows_pid, signal.CTRL_C_EVENT)
            # subprocess.Popen("taskkill /F /T /PID %i" % g_windows_pid, shell=True)
            for proc in psutil.process_iter():
                if proc.name() == "ffmpeg.exe" or proc.name() == "CorruptVideoInspector.exe":
                    proc.kill()
    except Exception as e:
        omniLog(f'ERROR in "kill_ffmpeg": {e}\n', log_file)
    root.destroy()


def estimatedTime(total_videos):
    # estimating 3 mins per 2GB video file, on average
    total_minutes = total_videos * 3
    # Get hours with floor division
    hours = total_minutes // 60
    # Get additional minutes with modulus
    minutes = total_minutes % 60
    # Create time as a string
    time_string = "{} hours, {} minutes".format(hours, minutes)
    return time_string


def calculateProgress(count, total):
    return "{0}%".format(int((count / total) * 100))

def inspectVideoFiles(directory, tkinter_window, listbox_completed_videos, index_start, progress_bar):
    try:
        global g_count
        global g_currently_processing
        global g_progress
        global g_force_cancel_thread
        global log_file

        omniLog('CREATED: _Logs.log\nCREATED: _Results.csv\n=================================================================\n', log_file)

        # CSV Results file
        results_file_path = os.path.join(directory, '_Results.csv')
        results_file_exists = os.path.isfile(results_file_path)
        if results_file_exists:
            os.remove(results_file_path)

        results_file = open(results_file_path, 'a+', encoding="utf8", newline='')
        results_file_writer = csv.writer(results_file)

        header = ['Video File', 'Corrupted']
        results_file_writer.writerow(header)
        results_file.flush()

        totalVideoFiles = countAllVideoFiles(directory)
        start_time = datetime.now().strftime('%Y-%m-%d %I:%M %p')

        omniLog(f'DIRECTORY: {directory}\n'
            f'TOTAL VIDEO FILES FOUND: {totalVideoFiles}\n'
            f'STARTING FROM VIDEO INDEX: {index_start}\n'
            f'START TIME: {start_time}\n'
            '=================================================================\n'
            '(DURATION IS IN HOURS:MINUTES:SECONDS)\n', log_file)

        all_videos_found = []
        for root, dirs, files in os.walk(directory):
            for filename in files:
                if filename.lower().endswith(tuple(VIDEO_EXTENSIONS)):
                    video_obj = VideoObject(filename, os.path.join(root, filename))
                    all_videos_found.append(video_obj)

        # Alphabetize list
        all_videos_found.sort(key=lambda x: x.filename)
        
        def clickReveal(evt):
            lb = evt.widget
            values = [lb.get(i) for i in lb.curselection()]
            paths = []
            for value in values:
                print("get path for", value)
                paths+=[x.full_filepath for x in all_videos_found if x.filename == value]
            print("selection:", paths)
            tkinter_window.clipboard_clear()
            tkinter_window.clipboard_append(",\n".join(paths))
            
        listbox_completed_videos.bind('<<ListboxSelect>>', clickReveal)

        count = 0
        process_errors = 0
        for video in all_videos_found:
            if g_force_cancel_thread: #This is set if we cancel ffmpeg...
            #If we kill ffmpeg but don't stop the thread it may just start another.
                print("Received kill signal for process thread...")
                break
            if (index_start > count + 1):
                count += 1
                continue

            start_time = time.time()

            g_progress.set(calculateProgress(count, totalVideoFiles))
            tkinter_window.update()

            g_count.set(f"{count + 1} ({process_errors}) / {totalVideoFiles}")
            tkinter_window.update()

            g_currently_processing.set(truncateFilename(video.filename))
            tkinter_window.update()

            proc = ''
            if isLinuxOs(): #apparently Linux may also register as Mac, so check Linux first
                global g_lin_pid
                #Assuming linux user has ffmpeg installed, e.g. via apt install ffmpeg.
                proc = subprocess.Popen(f'ffmpeg -v error -i {shlex.quote(video.full_filepath)} -f null - 2>&1', shell=True,
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                g_lin_pid = proc.pid
            elif isMacOs():
                global g_mac_pid
                proc = subprocess.Popen(f'./ffmpeg -v error -i {shlex.quote(video.full_filepath)} -f null - 2>&1', shell=True,
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                g_mac_pid = proc.pid
            elif isWindowsOs():
                global g_windows_pid
                ffmpeg_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'ffmpeg.exe'))
                proc = subprocess.Popen(f'"{ffmpeg_path}" -v error -i "{video.full_filepath}" -f null error.log', shell=True,
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                g_windows_pid = proc.pid
            
            output, error = proc.communicate()

            # Debug
            print(f'output= {output}\n')
            print(f'error= {error}\n')

            row_index = count
            if (index_start != 1):
                row_index = (count + 1) - index_start

            ffmpeg_result = ''
            if isWindowsOs():
                ffmpeg_result = error
            else:
                ffmpeg_result = output

            elapsed_time = time.time() - start_time
            readable_time = convertTime(elapsed_time)
            row = ''
            if not ffmpeg_result:
                # Healthy
                print("\033[92m{0}\033[00m".format("HEALTHY -> {}, [T={}]".format(video.filename, readable_time)), end='\n')  # green

                log_file.write('=================================================================\n')
                log_file.write(f'{video.filename}\n')
                log_file.write('STATUS: ✓ HEALTHY ✓\n')
                log_file.write(f'DURATION: {readable_time}\n')
                log_file.flush()

                row = [video.filename, 0]
                listbox_completed_videos.insert(tk.END, f'{video.filename}')
                listbox_completed_videos.itemconfig(row_index, bg='green')
                tkinter_window.update()
            else:
                # Corrupt
                process_errors += 1
                print("\033[31m{0}\033[00m".format("CORRUPTED -> {}, [T={}]".format(video.filename, readable_time)), end='\n')  # red

                log_file.write('=================================================================\n')
                log_file.write(f'{video.filename}\n')
                log_file.write('STATUS: X CORRUPT X\n')
                log_file.write(f'DURATION: {readable_time}\n')
                log_file.flush()

                row = [video.filename, 1]
                listbox_completed_videos.insert(tk.END, f'{video.filename}')
                listbox_completed_videos.itemconfig(row_index, bg='red')
                tkinter_window.update()

            results_file_writer.writerow(row)
            results_file.flush()

            count += 1

            g_progress.set(calculateProgress(count, totalVideoFiles))
            tkinter_window.update()

        g_count.set("---")
        g_currently_processing.set("N/A")
        progress_bar.stop()
        progress_bar['value'] = 100
        tkinter_window.update()

        results_file.flush()
        results_file.close()

        end_time = datetime.now().strftime('%Y-%m-%d %I:%M %p')

        print(f'Finished: {end_time}')
        omniLog(f'=================================================================\n'
            'SUCCESSFULLY PROCESSED {(totalVideoFiles + 1) - index_start} VIDEO FILES\n'
            'END TIME: {end_time}\n'
            '=================================================================\n', log_file)
        log_file.close()
        log_file=None
        g_force_cancel_thread = True #set the end flag to notify the exit function that the thread's already done
    except Exception as e:
        omniLog(f'ERROR in "inspectVideoFiles" (aka main thread): {e}\n',log_file)

def start_program(directory, root, index_start, label_chosen_directory, label_chosen_directory_var, label_video_count, label_video_count_var, label_index_start, entry_index_input, label_explanation, button_start, scrollframe, x_scrollbar, y_scrollbar, listbox_completed_videos):
    global log_file
    try:
        label_chosen_directory.destroy()
        label_chosen_directory_var.destroy()
        label_video_count.destroy()
        label_video_count_var.destroy()
        label_index_start.destroy()
        entry_index_input.destroy()
        label_explanation.destroy()
        button_start.destroy()
        listbox_completed_videos.destroy()
        x_scrollbar.destroy()
        y_scrollbar.destroy()
        scrollframe.destroy()

        label_progress_text = tk.Label(root, text="Progress:", font=('Helvetica Bold', 18))
        label_progress_text.pack(fill=tk.X, pady=10)

        g_progress.set("0%")
        label_progress_var = tk.Label(root, textvariable=g_progress, font=('Helvetica', 50))
        label_progress_var.pack(fill=tk.X, pady=(0, 10))

        progress_bar = ttk.Progressbar(root, orient="horizontal", mode="indeterminate", length=300)
        progress_bar.pack(pady=(0, 20))
        progress_bar.start()

        label_currently_processing_text = tk.Label(root, text="Currently Processing:", font=('Helvetica Bold', 18))
        label_currently_processing_text.pack(fill=tk.X, pady=10)

        g_count.set("0 / 0")
        label_count_var = tk.Label(root, textvariable=g_count, font=('Helvetica', 16))
        label_count_var.pack(fill=tk.X, pady=(0, 10))
        
        label_currently_processing_text = tk.Label(root, text="Good / Corrupt:", font=('Helvetica Bold', 16))
        label_currently_processing_text.pack(fill=tk.X, pady=10)

        g_currently_processing.set("N/A")
        label_currently_processing_var = tk.Label(root, textvariable=g_currently_processing, font=('Helvetica', 16))
        label_currently_processing_var.pack(fill=tk.X, pady=(0, 10))

        scrollframe = tk.Frame(root)
        scrollframe.pack(side=tk.TOP, expand=1, fill=tk.BOTH, pady=(0, 10))
        
        listbox_completed_videos = tk.Listbox(scrollframe, font=('Courier', 16)) #Using serif font to show I/l/O/0/etc. more clearly
        listbox_completed_videos.pack(expand=1, fill=tk.BOTH, side=tk.LEFT, pady=10)
        listbox_completed_videos.bind('<<ListboxSelect>>', lambda e: "break")
        #listbox_completed_videos.bind('<Button-1>', lambda e: "break")
        #listbox_completed_videos.bind('<Button-2>', lambda e: "break")
        #listbox_completed_videos.bind('<Button-3>', lambda e: "break")
        #listbox_completed_videos.bind('<ButtonRelease-1>', lambda e: "break")
        #listbox_completed_videos.bind('<Double-1>', lambda e: "break")
        #listbox_completed_videos.bind('<Double-Button-1>', lambda e: "break")
        #listbox_completed_videos.bind('<B1-Motion>', lambda e: "break")
        
        y_scrollbar = tk.Scrollbar(scrollframe, orient=tk.VERTICAL, command=listbox_completed_videos.yview)
        y_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        listbox_completed_videos.config(yscrollcommand=y_scrollbar.set)
            
        x_scrollbar = tk.Scrollbar(root, orient=tk.HORIZONTAL, command=listbox_completed_videos.xview)
        x_scrollbar.pack(side=tk.TOP, fill=tk.X, pady=10)
        listbox_completed_videos.config(xscrollcommand=x_scrollbar.set)

        button_ffmpeg_verify = Button(root, text="ffmpeg Status", width=200, command=lambda: verify_ffmpeg_still_running(root))
        button_ffmpeg_verify.pack(pady=10)

        if isMacOs(): #similar fix for mac-specific button issue - the 'borderless' field doesn't exist off of Mac
            # https://stackoverflow.com/questions/1529847/how-to-change-the-foreground-or-background-colour-of-a-tkinter-button-on-mac-os
            button_kill_ffmpeg = Button(root, background='#E34234', borderless=1, foreground='white', text="Safely Quit", width=500, command=lambda: kill_ffmpeg_warning(root))
        else: #Linux works fine with Windows settings for button
            button_kill_ffmpeg = Button(root, background='#E34234', foreground='white', text="Safely Quit", width=200, command=lambda: kill_ffmpeg_warning(root))
        button_kill_ffmpeg.pack(pady=10)

        thread = Thread(target=inspectVideoFiles, args=(directory, root, listbox_completed_videos, index_start, progress_bar))
        thread.start()
    except Exception as e:
        log_file.write(f'ERROR in "start_program": {e}\n')
        log_file.flush()

def afterDirectoryChosen(root, directory):
    # Log file
    log_file_path = os.path.join(directory, '_Logs.log')
    log_file_exists = os.path.isfile(log_file_path)
    if log_file_exists:
        os.remove(log_file_path)
    global log_file
    log_file = open(log_file_path, 'a', encoding="utf8")

    # Logging
    print('CORRUPT VIDEO FILE INSPECTOR')
    print('')
    log_file.write('=================================================================\n')
    log_file.write('                CORRUPT VIDEO FILE INSPECTOR\n')
    log_file.write('=================================================================\n')
    log_file.flush()

    totalVideos = countAllVideoFiles(directory)

    label_chosen_directory = tk.Label(root, text="Chosen directory:", font=('Helvetica Bold', 18))
    label_chosen_directory.pack(fill=tk.X, pady=5)
    label_chosen_directory_var = tk.Label(root, wraplength=450, text=f"{directory}", font=('Helvetica', 14))
    label_chosen_directory_var.pack(fill=tk.X, pady=(5, 20))

    label_video_count = tk.Label(root, text="Total number of videos found:", font=('Helvetica Bold', 18))
    label_video_count.pack(fill=tk.X, pady=5)
    label_video_count_var = tk.Label(root, text=f"{totalVideos}", font=('Helvetica', 16))
    label_video_count_var.pack(fill=tk.X, pady=(5, 20))

    scrollframe = tk.Frame(root)
    scrollframe.pack(side=tk.TOP, expand=1, fill=tk.BOTH)
        
    listbox_videos_found_with_index = tk.Listbox(scrollframe, font=('Courier', 16))
    listbox_videos_found_with_index.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, pady=10)
    listbox_videos_found_with_index.bind('<<ListboxSelect>>', lambda e: "break")
    listbox_videos_found_with_index.bind('<Button-1>', lambda e: "break")
    listbox_videos_found_with_index.bind('<Button-2>', lambda e: "break")
    listbox_videos_found_with_index.bind('<Button-3>', lambda e: "break")
    listbox_videos_found_with_index.bind('<ButtonRelease-1>', lambda e: "break")
    listbox_videos_found_with_index.bind('<Double-1>', lambda e: "break")
    listbox_videos_found_with_index.bind('<Double-Button-1>', lambda e: "break")
    listbox_videos_found_with_index.bind('<B1-Motion>', lambda e: "break")
    
    y_scrollbar = tk.Scrollbar(scrollframe, orient=tk.VERTICAL, command=listbox_videos_found_with_index.yview)
    y_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    listbox_videos_found_with_index.config(yscrollcommand=y_scrollbar.set)
        
    x_scrollbar = tk.Scrollbar(root, orient=tk.HORIZONTAL, command=listbox_videos_found_with_index.xview)
    x_scrollbar.pack(side=tk.TOP, fill=tk.X, pady=10)
    listbox_videos_found_with_index.config(xscrollcommand=x_scrollbar.set)

    all_videos_found = getAllVideoFiles(directory)
    for video in all_videos_found:
        listbox_videos_found_with_index.insert(tk.END, video)
    root.update()

    label_index_start = tk.Label(root,
                                 text=f"Start at video index (1 - {countAllVideoFiles(directory)}):",
                                 font=('Helvetica Bold', 18))
    label_index_start.pack(fill=tk.X, pady=5)

    entry_index_input = tk.Entry(root, width=50)
    entry_index_input.focus_set()
    entry_index_input.insert(tk.END, '1')
    entry_index_input.pack(fill=tk.X, padx=200)

    label_explanation = tk.Label(root, wraplength=450,
                                 text="The default is '1'. Set index to '1' if you want to start from the beginning and process all videos. If you are resuming a previous operation, then set the index to the desired number. Also note, each run will overwrite the _Logs and _Results files.",
                                 font=('Helvetica Italic', 12))
    label_explanation.pack(fill=tk.X, pady=5, padx=20)

    if totalVideos > 0:
        button_start = Button(root, text="Start Inspecting", width=25, command=lambda: start_program(directory, root, int(entry_index_input.get()), label_chosen_directory, label_chosen_directory_var, label_video_count, label_video_count_var, label_index_start, entry_index_input, label_explanation, button_start, scrollframe, x_scrollbar, y_scrollbar, listbox_videos_found_with_index))
        button_start.pack(pady=20)
    else:
        root.withdraw()
        error_window = tk.Toplevel(root)
        error_window.resizable(False, False)
        error_window.geometry("400x200")
        error_window.title("Error")

        label_error_msg = tk.Label(error_window, width=375, text="No video files found in selected directory!", font=('Helvetica', 14))
        label_error_msg.pack(fill=tk.X, pady=20)

        button_exit = Button(error_window, text="Exit", width=30, command=lambda: exit())
        button_exit.pack()

# ========================= MAIN ==========================

if not (isLinuxOs() or isMacOs() or isWindowsOs()):
    exit(1)
print("Linux:", isLinuxOs())
print("Mac:", isMacOs())
print("Windows:", isWindowsOs())

root = tk.Tk()
root.title("Corrupt Video Inspector")
try:
    if isLinuxOs(): #start button appears offscreen if using mac dimensions
        root.geometry("600x800")
        icon_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'icon.png'))
        root.iconphoto(False, tk.PhotoImage(file=icon_path))
    elif isMacOs():
        root.geometry("500x650")
    elif isWindowsOs():
        root.geometry("500x750")
        icon_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'icon.ico'))
        root.iconbitmap(default=icon_path)
except _tkinter.TclError as e: #assorted icon errors if someone's running this from source in a different folder
    print(e)
g_progress = tk.StringVar()
g_count = tk.StringVar()
g_currently_processing = tk.StringVar()
g_force_cancel_thread = False
g_mac_pid = ''
g_lin_pid = ''
g_windows_pid = ''
log_file = None

label_select_directory = tk.Label(root, wraplength=450, justify="left", text="Select a directory to search for all video files within the chosen directory and all of its containing subdirectories", font=('Helvetica', 16))
label_select_directory.pack(fill=tk.X, pady=20, padx=20)

button_select_directory = Button(root, text="Select Directory", width=20, command=lambda: selectDirectory(root, label_select_directory, button_select_directory))
button_select_directory.pack(pady=20)

#Handle proper shutdown of subprocess on window close:
root.protocol("WM_DELETE_WINDOW", lambda: kill_ffmpeg_warning(root))

root.mainloop()
