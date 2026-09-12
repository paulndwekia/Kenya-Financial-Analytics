# -*- coding: utf-8 -*-
"""Standalone Windows desktop shell for Kenya Financial Analytics."""
from __future__ import annotations
import os, sys, socket, subprocess, time, threading
from pathlib import Path

APP_NAME='Kenya Financial Analytics'
HOST='127.0.0.1'


def app_dir():
    return Path(sys.executable).resolve().parent if getattr(sys,'frozen',False) else Path(__file__).resolve().parent

def resource_dir():
    return Path(getattr(sys,'_MEIPASS',app_dir()))

def free_port():
    with socket.socket() as s:
        s.bind((HOST,0)); return s.getsockname()[1]

def wait_port(port, timeout=90):
    end=time.time()+timeout
    while time.time()<end:
        try:
            with socket.create_connection((HOST,port),.5): return True
        except OSError: time.sleep(.25)
    return False

def start_streamlit(port):
    root=app_dir(); dash=resource_dir()/'dashboard_desktop.py'
    os.environ['KFA_DATA_DIR']=str(root)
    env=os.environ.copy(); env['KFA_DATA_DIR']=str(root); env['PYTHONIOENCODING']='utf-8'
    if getattr(sys,'frozen',False):
        from streamlit.web import bootstrap
        args=[str(dash),'--server.address',HOST,'--server.port',str(port),'--server.headless','true','--browser.gatherUsageStats','false']
        flags={'server.address':HOST,'server.port':port,'server.headless':True,'browser.gatherUsageStats':False}
        bootstrap.run(str(dash),args,flags)
        return None
    py=root/'.venv'/'Scripts'/'python.exe'
    if not py.exists(): py=Path(sys.executable)
    return subprocess.Popen([str(py),'-m','streamlit','run',str(dash),'--server.address',HOST,'--server.port',str(port),'--server.headless','true','--browser.gatherUsageStats','false'],cwd=str(root),env=env,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))

def main():
    port=free_port(); proc=None
    try:
        if getattr(sys,'frozen',False): threading.Thread(target=start_streamlit,args=(port,),daemon=True).start()
        else: proc=start_streamlit(port)
        if not wait_port(port): raise RuntimeError('Dashboard did not start within 90 seconds.')
        url=f'http://{HOST}:{port}'
        try:
            import webview
            webview.create_window(APP_NAME,url,width=1500,height=950,min_size=(1100,700),resizable=True,text_select=True)
            webview.start()
        except Exception:
            import webbrowser
            webbrowser.open(url)
            input('Kenya Financial Analytics is running. Press Enter to close...')
    except Exception as e:
        try:
            import tkinter as tk
            from tkinter import messagebox
            r=tk.Tk(); r.withdraw(); messagebox.showerror(APP_NAME,f'Failed to start.\n\n{type(e).__name__}: {e}'); r.destroy()
        except Exception: pass
    finally:
        if proc is not None and proc.poll() is None:
            proc.terminate()

if __name__=='__main__': main()
