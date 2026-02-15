; Script de Inno Setup para Mux Programming Language
; Creador: MushhX

#define MyAppName "Mux Programming Language"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "MushhX"
#define MyAppURL "https://github.com/mushhx/mux"
#define MyAppExeName "mux.exe"

[Setup]
; Información de la aplicación
AppId={{8F9A2B3C-4D5E-6F7A-8B9C-0D1E2F3A4B5C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={autopf}\Mux
DefaultGroupName=Mux Programming Language
AllowNoIcons=yes
LicenseFile=LICENSE
InfoBeforeFile=INSTALL.md
OutputDir=installer_output
OutputBaseFilename=mux-setup-{#MyAppVersion}
SetupIconFile=mux_icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=lowest
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "addtopath"; Description: "Agregar Mux al PATH del sistema"; GroupDescription: "Opciones del sistema:"; Flags: unchecked

[Files]
; Ejecutable principal
Source: "dist\mux.exe"; DestDir: "{app}"; Flags: ignoreversion

; Librería estándar
Source: "mux_lang\stdlib\*"; DestDir: "{app}\mux_lang\stdlib"; Flags: ignoreversion recursesubdirs createallsubdirs

; Ejemplos
Source: "examples\*"; DestDir: "{app}\examples"; Flags: ignoreversion recursesubdirs createallsubdirs

; Documentación
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion isreadme
Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "QUICKSTART.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "FEATURES.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "STDLIB_REFERENCE.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "UNIQUE_COMMANDS.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "BOTS_GUIDE.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "EXECUTABLE_GUIDE.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Mux Programming Language"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Ejemplos"; Filename: "{app}\examples"
Name: "{group}\Documentación"; Filename: "{app}\README.md"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Mux"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\README.md"; Description: "Ver documentación"; Flags: postinstall shellexec skipifsilent unchecked
Filename: "{app}\examples"; Description: "Abrir carpeta de ejemplos"; Flags: postinstall shellexec skipifsilent unchecked

[Registry]
; Agregar al PATH si el usuario lo seleccionó
Root: HKCU; Subkey: "Environment"; ValueType: expandsz; ValueName: "Path"; ValueData: "{olddata};{app}"; Tasks: addtopath; Check: NeedsAddPath('{app}')

[Code]
function NeedsAddPath(Param: string): boolean;
var
  OrigPath: string;
begin
  if not RegQueryStringValue(HKEY_CURRENT_USER, 'Environment', 'Path', OrigPath)
  then begin
    Result := True;
    exit;
  end;
  Result := Pos(';' + Param + ';', ';' + OrigPath + ';') = 0;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    // Crear archivo de versión
    SaveStringToFile(ExpandConstant('{app}\VERSION.txt'), 
      'Mux Programming Language' + #13#10 +
      'Version: {#MyAppVersion}' + #13#10 +
      'Build Date: ' + GetDateTimeString('yyyy-mm-dd', '-', ':') + #13#10 +
      'Platform: Windows x64' + #13#10 +
      'Creador: MushhX' + #13#10, False);
  end;
end;

[Messages]
WelcomeLabel1=Bienvenido al Asistente de Instalación de [name]
WelcomeLabel2=Este programa instalará [name/ver] en tu computadora.%n%nMux es un lenguaje de programación moderno, accesible y ligero diseñado para que cualquiera pueda aprenderlo en horas y usarlo en proyectos reales en días.%n%nSe recomienda cerrar todas las demás aplicaciones antes de continuar.
FinishedHeadingLabel=Completando el Asistente de Instalación de [name]
FinishedLabel=[name] ha sido instalado en tu computadora.%n%nPuedes ejecutar Mux desde la línea de comandos usando:%n%n  mux archivo.mux%n%nO explorar los ejemplos incluidos en la carpeta de instalación.
