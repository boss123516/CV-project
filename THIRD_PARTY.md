# Third-party sources

- Source: https://github.com/cyberbotics/webots/tree/R2025a/projects/humans/pedestrian
- Version: R2025a (matching the installed simulator).
- `webots/protos/vendor/Pedestrian*.proto`: Cyberbotics pedestrian model and geometry; original headers retained; trailing empty lines normalized. These assets are **licensed for use only with Webots**, per https://cyberbotics.com/webots_assets_license . The repository's general Apache license does not override these asset headers.
- `webots/controllers/assistive_walker/upstream_pedestrian.py`: official Python pedestrian controller, Copyright 1996–2024 Cyberbotics Ltd., Apache License 2.0. Adaptation: wrapped its original entrypoint in `if __name__ == '__main__'` so the gait class can be reused. Original license notice retained. https://www.apache.org/licenses/LICENSE-2.0
- Bench, cone, sidewalk, rig and cane: generated from native Webots primitives in `scripts/build_world.py` for this project.
- Speech uses the installed system `libespeak-ng` and Korean language data through its public C API. https://github.com/espeak-ng/espeak-ng
