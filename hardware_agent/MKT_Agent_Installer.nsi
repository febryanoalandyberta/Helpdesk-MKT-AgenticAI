!define PRODUCT_NAME "MKT Hardware Agent"
!define PRODUCT_VERSION "1.0.0"
!define PRODUCT_PUBLISHER "PT Megakreasi Tech"
!define EXE_NAME "mkt_hardware_agent.exe"

SetCompressor lzma
OutFile "MKT_Agent_Installer_v${PRODUCT_VERSION}.exe"
InstallDir "$PROGRAMFILES64\MKT Helpdesk AI\Hardware Agent"
RequestExecutionLevel admin

Section "MainSection" SEC01
  SetOutPath "$INSTDIR"
  
  ; Hentikan proses jika sedang berjalan
  ExecWait 'taskkill /F /IM ${EXE_NAME}'
  
  ; Copy compiled Rust executable
  File "src-tauri\target\release\${EXE_NAME}"
  
  ; Write registry for AutoStart
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Run" "MKT_Hardware_Agent" '"$INSTDIR\${EXE_NAME}"'
  
  ; Create Uninstaller
  WriteUninstaller "$INSTDIR\uninst.exe"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\MKT_Hardware_Agent" "DisplayName" "${PRODUCT_NAME}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\MKT_Hardware_Agent" "UninstallString" '"$INSTDIR\uninst.exe"'
  
  ; Start immediately after installation
  ExecShell "" "$INSTDIR\${EXE_NAME}"
SectionEnd

Section Uninstall
  ExecWait 'taskkill /F /IM ${EXE_NAME}'
  Delete "$INSTDIR\${EXE_NAME}"
  Delete "$INSTDIR\uninst.exe"
  DeleteRegValue HKLM "Software\Microsoft\Windows\CurrentVersion\Run" "MKT_Hardware_Agent"
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\MKT_Hardware_Agent"
  RMDir "$INSTDIR"
SectionEnd
