import wmi
c = wmi.WMI()
for m in c.Win32_DesktopMonitor():
    print(m.DeviceID, m.Name, m.Availability, m.Status)
