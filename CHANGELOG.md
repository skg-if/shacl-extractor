# 1.0.0 (2026-03-30)


* build!: drop Python 3.9 support ([6c42de5](https://github.com/skg-if/shacl-extractor/commit/6c42de50dc1f3d35ddc1ca24c9a02875bd95ffde))
* feat!: replace hardcoded root classes with --root-classes option ([75a4877](https://github.com/skg-if/shacl-extractor/commit/75a4877dfeaa38c55e8c6c957bcb14e2ad7f9cc3))


### Bug Fixes

* add _get_ext_module_name() ([14b4f51](https://github.com/skg-if/shacl-extractor/commit/14b4f51a8a417876c8e1e8d81da0cc12c82d6ef8))
* **ci:** pass --repo to gh run list in deploy workflow ([ecf0ef5](https://github.com/skg-if/shacl-extractor/commit/ecf0ef55d7d1888805c0db8a45dca5c0b755d7bf))
* Configure submodules to track main branch for automatic updates ([40dde9e](https://github.com/skg-if/shacl-extractor/commit/40dde9e4007d76c9b4a4524749f7051b824cd6a2))
* correct version detection logic for modular ontology structure ([a4a632e](https://github.com/skg-if/shacl-extractor/commit/a4a632e0c9a706b9b78e679a586bf3f42fe85e91))
* generate per-module SHACL shapes with separate namespaces ([1284312](https://github.com/skg-if/shacl-extractor/commit/1284312256c7865a255fb85b4c9fd2dfcb4fb604))
* generate sh:or for union range properties ([18c889c](https://github.com/skg-if/shacl-extractor/commit/18c889c4948a8f30af6651fe2d1f5174fd4cc867)), closes [#4](https://github.com/skg-if/shacl-extractor/issues/4)
* improve error handling and test coverage ([e49d3a5](https://github.com/skg-if/shacl-extractor/commit/e49d3a5171a324f8746ac33ef053e09eac4a933e))
* make critical properties mandatory in SHACL shapes ([8dbd7e0](https://github.com/skg-if/shacl-extractor/commit/8dbd7e0e0f4bd70a33930855ad7c397e31eb9957))
* recognize rdfs:langString as a literal type in shape generation ([1b65205](https://github.com/skg-if/shacl-extractor/commit/1b65205aa64e11a35c66f5c2a93ceab8f6d1875d))
* use ext-*** directory name as module name for local extension paths ([aaec6fb](https://github.com/skg-if/shacl-extractor/commit/aaec6fbc85a9cea7595adf2c4c192e291f83e850))


### Features

* generate sh:in for controlled vocabulary properties ([9b3b90f](https://github.com/skg-if/shacl-extractor/commit/9b3b90f19c8d209dae082b55a013aefedb531d2a))


### BREAKING CHANGES

* modular directory inputs no longer get SKG-IF root
classes automatically. Pass --root-classes presets/skg-if-core.json
to restore the previous behavior.
* minimum required Python version is now 3.10.
