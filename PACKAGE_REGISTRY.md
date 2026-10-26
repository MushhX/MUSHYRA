# Registro y publicación de paquetes Mux

`mux-pkg` puede leer un índice JSON local o HTTPS. El proyecto proporciona el cliente y el formato; cada equipo debe alojar el índice, distribuir su trust store público y proteger su clave privada.

## Preparar un paquete firmado

La carpeta admite `.mux`, `.json`, `.md` y `.txt`. Incluye `mux-package.json` con nombre, versión, entrada, dependencias y los hashes de cada archivo del paquete, excepto el propio manifiesto:

```json
{
  "name": "saludos",
  "version": "1.2.0",
  "description": "Funciones de saludo",
  "main": "main.mux",
  "dependencies": {},
  "files": {}
}
```

1. Calcula el mapa `files` desde la carpeta y copia el resultado JSON en el manifiesto:

   ```console
   mux-pkg hashes ./saludos
   ```

2. Genera una clave Ed25519 una sola vez. Guarda la privada fuera del repositorio y conserva el archivo público como trust store para compartirlo por un canal autenticado:

   ```console
   mux-pkg keygen equipo-2026 --private-key C:/secrets/mux-signing.key --trust-store C:/secrets/mux-trust.json
   ```

3. Firma el manifiesto y crea el ZIP. Si cambias cualquier archivo después de calcular `files`, vuelve a calcular los hashes y firmar:

   ```console
   mux-pkg sign ./saludos/mux-package.json --private-key C:/secrets/mux-signing.key --key-id equipo-2026
   mux-pkg pack ./saludos --output ./dist/saludos-1.2.0.zip
   ```

4. Publica el ZIP en HTTPS y prepara un índice con su hash:

   ```json
   {
     "schema_version": 1,
     "packages": [
       {
         "name": "saludos",
         "version": "1.2.0",
         "description": "Funciones de saludo",
         "url": "https://packages.example.org/saludos-1.2.0.zip",
         "sha256": "HASH_SHA256_DEL_ZIP"
       }
     ]
   }
   ```

5. Firma el índice y publícalo por HTTPS. El mismo formato firmado se puede guardar como archivo local durante el desarrollo:

   ```console
   mux-pkg sign ./index.json --private-key C:/secrets/mux-signing.key --key-id equipo-2026
   ```

La firma del índice vincula nombre, versión, URL y hash del ZIP. La firma del manifiesto vincula sus metadatos y el mapa `files`; el cliente compara el mapa con los archivos descargados antes de instalarlos. No firmes ni publiques un paquete antes de comprobar su contenido.

## Configurar el cliente

Guarda el trust store recibido en una ruta protegida y define el índice por variable de entorno o argumento:

```console
set MUX_PACKAGE_REGISTRY=https://packages.example.org/index.json
mux-pkg search saludos --trust-store C:/config/mux-trust.json
mux-pkg install saludos --from-registry --trust-store C:/config/mux-trust.json
mux-pkg update saludos --trust-store C:/config/mux-trust.json
```

En PowerShell usa `$env:MUX_PACKAGE_REGISTRY = 'https://packages.example.org/index.json'`. El índice remoto y las descargas deben usar HTTPS con direcciones IP públicas; se validan redirecciones, tamaños, rutas ZIP y firmas. Un índice local puede ser útil para desarrollo, pero no establece por sí solo una raíz de confianza.

## Versiones y lockfiles

Las versiones siguen `MAJOR.MINOR.PATCH` y admiten prerelease/build metadata. Las dependencias permiten versión exacta, `>=`, `^`, `~` o `*`. El cliente instala primero dependencias presentes en el lockfile:

```console
mux-pkg lock --manifest mux-package.json --output mux.lock.json
mux-pkg install-lock --file mux.lock.json --trust-store C:/config/mux-trust.json
```

El lockfile fija versión, origen y SHA-256 del paquete. Mantén el lockfile junto al manifiesto si necesitas instalaciones repetibles. Los paquetes instalados se pueden revisar con `mux-pkg verify` y `mux-pkg audit`; `mux-pkg outdated` consulta el índice configurado.

El hash SHA-256 detecta cambios respecto del valor fijado. La autenticidad depende de que el trust store llegue al usuario por un canal confiable y de que la clave privada siga protegida. Mux no aloja un registro ni una clave oficial.
