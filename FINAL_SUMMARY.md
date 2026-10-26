# Estado del proyecto

MUSHYRA contiene un intérprete, una CLI `myr archivo.myr`, módulos estándar nativos y herramientas de desarrollo, además de un gestor local/remoto de paquetes y scripts para crear ejecutables e instaladores.

La versión del código está centralizada en `mushyra/_version.py`. Los binarios no se guardan en el repositorio: se generan localmente con `build_exe.py`, y el instalador Windows con `build_installer.py` e Inno Setup.

Para empezar, consulta [README.md](README.md). Las guías de instalación, módulos, bots y distribución describen los requisitos actuales.
