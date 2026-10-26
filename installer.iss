; Script de Inno Setup para MUSHYRA
; Creador: MushhX

#define MyAppName "MUSHYRA"
#define MyAppVersion "@MUX_VERSION@"
#define MyAppPublisher "MushhX"
#define MyAppURL "https://github.com/mushhx/mux"
#define MyAppExeName "myr.exe"

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
DefaultDirName={localappdata}\Programs\MUSHYRA
DefaultGroupName=MUSHYRA
AllowNoIcons=yes
LicenseFile=@MUX_ROOT@\LICENSE
InfoBeforeFile=@MUX_ROOT@\INSTALL.md
OutputDir=@MUX_OUTPUT_DIR@
OutputBaseFilename=mushyra-setup-{#MyAppVersion}
SetupIconFile=@MUX_ROOT@\mux_icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64
ArchitecturesAllowed=x64
PrivilegesRequired=lowest
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "addtopath"; Description: "Agregar MUSHYRA al PATH del usuario"; GroupDescription: "Opciones del sistema:"; Flags: unchecked

[Files]
; Ejecutable principal
Source: "@MUX_ROOT@\dist\myr.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "@MUX_ROOT@\dist\mux.exe"; DestDir: "{app}"; Flags: ignoreversion

; Ejemplos
Source: "@MUX_ROOT@\examples\*"; DestDir: "{app}\examples"; Flags: ignoreversion recursesubdirs createallsubdirs

; Documentación
Source: "@MUX_ROOT@\README.md"; DestDir: "{app}"; Flags: ignoreversion isreadme
Source: "@MUX_ROOT@\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "@MUX_ROOT@\QUICKSTART.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "@MUX_ROOT@\FEATURES.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "@MUX_ROOT@\STDLIB_REFERENCE.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "@MUX_ROOT@\UNIQUE_COMMANDS.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "@MUX_ROOT@\BOTS_GUIDE.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "@MUX_ROOT@\EXECUTABLE_GUIDE.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\MUSHYRA"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Ejemplos"; Filename: "{app}\examples"
Name: "{group}\Documentación"; Filename: "{app}\README.md"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\MUSHYRA"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\README.md"; Description: "Ver documentación"; Flags: postinstall shellexec skipifsilent unchecked
Filename: "{app}\examples"; Description: "Abrir carpeta de ejemplos"; Flags: postinstall shellexec skipifsilent unchecked

[Code]
function PathContains(PathValue, Candidate: string): boolean;
var
  Remaining, Item: string;
  SeparatorPosition: Integer;
begin
  Result := False;
  Remaining := PathValue;
  while Remaining <> '' do
  begin
    SeparatorPosition := Pos(';', Remaining);
    if SeparatorPosition = 0 then
    begin
      Item := Remaining;
      Remaining := '';
    end
    else
    begin
      Item := Copy(Remaining, 1, SeparatorPosition - 1);
      Delete(Remaining, 1, SeparatorPosition);
    end;
    if CompareText(Trim(Item), Candidate) = 0 then
    begin
      Result := True;
      exit;
    end;
  end;
end;

function RemovePathEntry(PathValue, Candidate: string): string;
var
  Remaining, Item: string;
  SeparatorPosition: Integer;
  FirstEntry: Boolean;
begin
  Result := '';
  Remaining := PathValue;
  FirstEntry := True;
  while Remaining <> '' do
  begin
    SeparatorPosition := Pos(';', Remaining);
    if SeparatorPosition = 0 then
    begin
      Item := Remaining;
      Remaining := '';
    end
    else
    begin
      Item := Copy(Remaining, 1, SeparatorPosition - 1);
      Delete(Remaining, 1, SeparatorPosition);
    end;
    if CompareText(Trim(Item), Candidate) <> 0 then
    begin
      if not FirstEntry then
        Result := Result + ';';
      Result := Result + Item;
      FirstEntry := False;
    end;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  OrigPath: string;
  NewPath: string;
begin
  if CurStep = ssPostInstall then
  begin
    // Crear archivo de versión
    SaveStringToFile(ExpandConstant('{app}\VERSION.txt'), 
      'MUSHYRA' + #13#10 +
      'Version: {#MyAppVersion}' + #13#10 +
      'Build Date: ' + GetDateTimeString('yyyy-mm-dd', '-', ':') + #13#10 +
      'Platform: Windows x64' + #13#10 +
      'Creador: MushhX' + #13#10, False);

    if WizardIsTaskSelected('addtopath') then
    begin
      OrigPath := '';
      RegQueryStringValue(HKEY_CURRENT_USER, 'Environment', 'Path', OrigPath);
      if not PathContains(OrigPath, ExpandConstant('{app}')) then
      begin
        if OrigPath = '' then
          NewPath := ExpandConstant('{app}')
        else
          NewPath := OrigPath + ';' + ExpandConstant('{app}');
        RegWriteExpandStringValue(HKEY_CURRENT_USER, 'Environment', 'Path', NewPath);
      end;
    end;
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  OrigPath: string;
begin
  if CurUninstallStep = usUninstall then
  begin
    if RegQueryStringValue(HKEY_CURRENT_USER, 'Environment', 'Path', OrigPath) and
       PathContains(OrigPath, ExpandConstant('{app}')) then
      RegWriteExpandStringValue(
        HKEY_CURRENT_USER, 'Environment', 'Path',
        RemovePathEntry(OrigPath, ExpandConstant('{app}')));
  end;
end;

[Messages]
WelcomeLabel1=Bienvenido al Asistente de Instalación de [name]
WelcomeLabel2=Este programa instalará [name/ver] en tu computadora.%n%nMUSHYRA es un lenguaje de programación moderno y ligero.%n%nSe recomienda cerrar todas las demás aplicaciones antes de continuar.
FinishedHeadingLabel=Completando el Asistente de Instalación de [name]
FinishedLabel=[name] ha sido instalado en tu computadora.%n%nPuedes ejecutar MUSHYRA desde la línea de comandos usando:%n%n  myr archivo.myr%n%nTambién puedes usar el alias mux con programas .mux existentes.
