"""
Sert l'app web (export Expo) depuis le backend : un seul service, une seule adresse, pas de CORS.

Cache : index.html et manifest.json sont toujours revalidés, pour qu'une mise à jour soit
prise en compte au lancement suivant ; les fichiers générés (noms à empreinte) sont gardés un an.
"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

IMMUTABLE_PREFIXES = ("_expo/static/", "assets/")


class WebAppFiles(StaticFiles):
    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        if response.status_code in (200, 304):
            immutable = path.startswith(IMMUTABLE_PREFIXES)
            response.headers["Cache-Control"] = (
                "public, max-age=31536000, immutable" if immutable else "no-cache"
            )
        return response


def mount_web_app(app: FastAPI, directory: str) -> bool:
    """À appeler APRÈS tous les routers (le montage à "/" capte tout ce qui n'a pas de route)."""
    root = Path(directory)
    if not (root / "index.html").is_file():
        return False
    app.mount("/", WebAppFiles(directory=str(root), html=True), name="web")
    return True
