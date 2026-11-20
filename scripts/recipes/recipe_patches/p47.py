"""Lot 47 : derniers signalements de l'audit de cohérence (2026-11-21)."""

PATCHES = {
    # le pain pita est réchauffé 1 minute à la poêle : la cuisson n'était pas comptée
    "wrap_falafel_tahini_6a2d73": [
        ("time", 15, 0, 2),
    ],
}
