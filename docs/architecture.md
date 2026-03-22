# GraphQLer Architecture

## Overview

GraphQLer is split into two sequential phases — **Compilation** and **Fuzzing** — connected by files on disk. The compiler produces YAML/JSON artifacts that the fuzzer reads at startup. Neither phase holds a direct reference to the other at runtime.

---

## Architecture Diagram

```mermaid
flowchart TD
    subgraph CLI["CLI — __main__.py"]
        ARGS["Argument Parser\n--mode / --url / --path\n--auth / --config / --proxy"]
        CONFIG_HANDLER["config_handler\nparse_config · set_config"]
        MODES["Modes\ncompile · compile-graph\ncompile-chains · fuzz\nidor · run · single"]
        CORE["core.py\ncompile_and_fuzz()\nProgrammatic API"]
    end

    subgraph COMPILER["Compiler — compiler/"]
        COMPILER_MAIN["Compiler\nsave_path · url"]

        subgraph INTROSPECT["Introspection"]
            INTRO_QUERY["introspection_query\n(standard)"]
            CLAIRV["clairvoyance\n(blind fallback)"]
        end

        subgraph PARSERS["Parsers — compiler/parsers/"]
            PARSER_BASE["Parser (base)"]
            QLP["QueryListParser"]
            MLP["MutationListParser"]
            OLP["ObjectListParser"]
            IOLP["InputObjectListParser"]
            ELP["EnumListParser"]
            ULP["UnionListParser"]
            ILP["InterfaceListParser"]
        end

        subgraph RESOLVERS["Resolvers — compiler/resolvers/"]
            RES_BASE["Resolver (base)"]
            ODR["ObjectDependencyResolver"]
            OMR["ObjectMethodResolver"]
            MOR["MutationObjectResolver"]
            QOR["QueryObjectResolver"]
            LLM_RES["LLMResolver (base)"]
            LLM_MOR["LLMMutationObjectResolver"]
            LLM_QOR["LLMQueryObjectResolver"]
            RES_CMP["ResolverComparison"]
        end

        subgraph GRAPH_GEN["Dependency Graph — graph/"]
            GRAPH_GENERATOR["GraphGenerator\nnetworkx.DiGraph"]
            NODE["Node\nname · graphql_type\ninputs · output"]
        end

        subgraph CHAIN_GEN["Chain Generation — chains/"]
            CG["ChainGenerator\nstrategy pattern"]
            subgraph STRATEGIES["Strategies"]
                TOPO["TopologicalChainStrategy"]
                IDOR_STRAT["IDORChainStrategy"]
            end
            subgraph IDOR_CLASS["IDOR Classifiers — chains/idor/"]
                HEUR["HeuristicIDORClassifier"]
                LLM_IDOR["LLMIDORClassifier\n(optional)"]
            end
            CHAIN["Chain\nsteps · reason · confidence\nis_multi_profile · nodes"]
            CHAIN_STEP["ChainStep\nnode · profile_name"]
        end
    end

    subgraph DISK["Disk — output_dir/"]
        direction LR
        YAML_RAW["Raw YAML\nobjects · queries · mutations\nenums · unions · interfaces\ninput_objects"]
        YAML_COMPILED["Compiled YAML\ncompiled/objects.yaml\ncompiled/queries.yaml\ncompiled/mutations.yaml"]
        CHAINS_YAML["compiled/chains.yaml"]
        GRAPH_PNG["dependency_graph.png"]
        INTROSPECTION_JSON["introspection_result.json"]
        STATS_FILES["stats.txt · stats.json\nlogs/fuzzer.log"]
        OBJECTS_PKL["objects_bucket.pkl"]
        DETECTIONS_DIR["detections/\n  VULN_NAME/NODE/\n    raw_log.txt\n    summary.txt"]
    end

    subgraph FUZZER["Fuzzer — fuzzer/"]
        FUZZER_MAIN["Fuzzer\nsave_path · url\nprofiles{primary,secondary}"]
        API_OBJ["API\nqueries · mutations · objects\nenums · unions · interfaces"]
        GRAPH_LOAD["GraphGenerator\nloads DiGraph from compiled YAML"]
        OBJECTS_BUCKET["ObjectsBucket\nobject store keyed by type\npickle-persisted"]

        subgraph FENGINE["FEngine — fuzzer/engine/fengine.py"]
            FENGINE_MAIN["FEngine ★ singleton\napi · logger"]
            subgraph MATERIALIZERS["Materializers — engine/materializers/"]
                MAT_BASE["Materializer (base)\nget_payload()"]
                REG_MAT["RegularPayloadMaterializer"]
                MAX_MAT["MaximalPayloadMaterializer"]
                INJ_MAT["InjectionMaterializer"]
                DOS_MAT["DoS Materializers\nalias · batch · deep-recursion"]
            end
            RETRIER["Retrier\nauto-fixes malformed requests"]
        end

        subgraph DENGINE["DEngine — fuzzer/engine/dengine.py"]
            DENGINE_MAIN["DEngine\napi · logger"]
            subgraph DETECTORS["Detectors — engine/detectors/"]
                DET_BASE["Detector (abstract base)\ndetect() · _is_vulnerable()\n_is_potentially_vulnerable()"]
                subgraph INJ_DETS["Injection Detectors"]
                    SQL_DET["SQLInjectionDetector"]
                    NOSQL_DET["NoSQLInjectionDetector"]
                    TSQL_DET["TimeSQLInjectionDetector"]
                    SSRF_DET["SSRFInjectionDetector"]
                    OS_DET["OSCommandInjectionDetector"]
                    XSS_DET["XSSInjectionDetector"]
                    PATH_DET["PathInjectionDetector"]
                end
                subgraph MISC_DETS["Misc Detectors"]
                    QDB_DET["QueryDenyBypassDetector"]
                end
                subgraph FIELD_DETS["Field Detectors"]
                    FCF_DET["FieldCharsetFuzzingDetector"]
                    IDE_DET["IDEnumerationDetector"]
                end
                subgraph API_DETS["API-Level Detectors"]
                    INTRO_DET["IntrospectionDetector"]
                    FS_DET["FieldSuggestionsDetector"]
                end
            end
        end

        IDOR_CHAIN_DET["IDORChainDetector\n(post-chain analysis)"]
        PROFILES["RuntimeProfile\nname · auth_token · headers"]
    end

    subgraph UTILS["Shared Utils — utils/"]
        STATS["Stats ★ singleton\nhttp_status_codes · vulnerabilities\nresults · timings · counts"]
        PLUGINS_HDR["plugins_handler\nget_request_utils()"]
        REQUEST_UTILS["RequestUtils\nsend_graphql_request()\nimplements RequestUtilsProtocol"]
        REQ_PROTO["RequestUtilsProtocol\n(interface — swappable)"]
        DET_WRITER["detection_writer\nwrite_from_detector()\nwrite_from_chain()"]
        LOGGER["Logger\ncompiler · fuzzer · detector"]
        CONFIG["config.py ⚠ global module\nAUTHORIZATION · IDOR_SECONDARY_AUTH\nMAX_TIME · detection flags\n50+ settings"]
    end

    %% ── CLI wiring ──────────────────────────────────────────────
    ARGS --> CONFIG_HANDLER --> CONFIG
    ARGS --> MODES
    MODES -->|"compile / run"| COMPILER_MAIN
    MODES -->|"fuzz / run / idor / single"| FUZZER_MAIN
    CORE --> COMPILER_MAIN
    CORE --> FUZZER_MAIN

    %% ── Compiler pipeline ────────────────────────────────────────
    COMPILER_MAIN --> INTROSPECT
    INTRO_QUERY --> INTROSPECTION_JSON
    CLAIRV --> INTROSPECTION_JSON
    INTROSPECTION_JSON --> PARSERS
    PARSERS --> YAML_RAW
    YAML_RAW --> RESOLVERS
    RES_BASE --> MOR & QOR
    LLM_RES --> LLM_MOR & LLM_QOR
    RESOLVERS --> YAML_COMPILED
    YAML_COMPILED --> GRAPH_GENERATOR
    GRAPH_GENERATOR --> NODE
    GRAPH_GENERATOR --> GRAPH_PNG
    GRAPH_GENERATOR --> CHAIN_GEN
    CG --> TOPO & IDOR_STRAT
    IDOR_STRAT --> HEUR
    IDOR_STRAT -.->|optional| LLM_IDOR
    CG --> CHAIN --> CHAIN_STEP
    CG --> CHAINS_YAML

    %% ── Fuzzer startup (reads disk) ──────────────────────────────
    YAML_COMPILED -->|read at init| API_OBJ
    YAML_COMPILED -->|read at init| GRAPH_LOAD
    CHAINS_YAML -->|loaded at init| FUZZER_MAIN
    OBJECTS_PKL -.->|optional load| OBJECTS_BUCKET

    %% ── Fuzzer runtime ───────────────────────────────────────────
    FUZZER_MAIN --> FENGINE_MAIN & DENGINE_MAIN & IDOR_CHAIN_DET
    FUZZER_MAIN --> API_OBJ & GRAPH_LOAD & OBJECTS_BUCKET
    FUZZER_MAIN --> PROFILES

    FENGINE_MAIN --> MAT_BASE
    MAT_BASE --> REG_MAT & MAX_MAT & INJ_MAT & DOS_MAT
    FENGINE_MAIN --> RETRIER
    FENGINE_MAIN --> OBJECTS_BUCKET

    DENGINE_MAIN --> DET_BASE
    DET_BASE --> INJ_DETS & MISC_DETS & FIELD_DETS & API_DETS
    INJ_DETS & MISC_DETS & FIELD_DETS --> STATS
    INJ_DETS & MISC_DETS & FIELD_DETS --> DET_WRITER

    IDOR_CHAIN_DET --> STATS
    IDOR_CHAIN_DET --> DET_WRITER

    %% ── Output ───────────────────────────────────────────────────
    STATS -->|save| STATS_FILES
    OBJECTS_BUCKET -->|save| OBJECTS_PKL
    DET_WRITER --> DETECTIONS_DIR

    %% ── Shared utils wiring ──────────────────────────────────────
    PLUGINS_HDR --> REQ_PROTO
    REQUEST_UTILS -.->|implements| REQ_PROTO
    COMPILER_MAIN & FENGINE_MAIN & DETECTORS --> PLUGINS_HDR

    %% ── Global config (tight coupling — dashed) ──────────────────
    CONFIG -.->|imported directly| COMPILER_MAIN
    CONFIG -.->|imported directly| FUZZER_MAIN
    CONFIG -.->|imported directly| FENGINE_MAIN
    CONFIG -.->|imported directly| DENGINE_MAIN
    CONFIG -.->|imported directly| STATS
    CONFIG -.->|imported directly| OBJECTS_BUCKET
    CONFIG -.->|imported directly| DET_WRITER
    CONFIG -.->|imported directly| CHAIN_GEN

    %% ── Styles ───────────────────────────────────────────────────
    classDef singleton fill:#f4a261,stroke:#e76f51,color:#000
    classDef tight_coupling fill:#e63946,stroke:#c1121f,color:#fff
    classDef interface fill:#2a9d8f,stroke:#21867a,color:#fff
    classDef disk fill:#457b9d,stroke:#1d3557,color:#fff
    classDef detector fill:#6a4c93,stroke:#4a3770,color:#fff

    class STATS,FENGINE_MAIN singleton
    class CONFIG tight_coupling
    class REQ_PROTO interface
    class YAML_RAW,YAML_COMPILED,CHAINS_YAML,INTROSPECTION_JSON,STATS_FILES,OBJECTS_PKL,DETECTIONS_DIR,GRAPH_PNG disk
    class SQL_DET,NOSQL_DET,TSQL_DET,SSRF_DET,OS_DET,XSS_DET,PATH_DET,QDB_DET,FCF_DET,IDE_DET,INTRO_DET,FS_DET,IDOR_CHAIN_DET detector
```

---

## Coupling Analysis

### ✅ Well-Decoupled

| Boundary | Mechanism | Notes |
|---|---|---|
| Compiler ↔ Fuzzer | **Files on disk** | Zero runtime coupling — compiler writes YAML/JSON, fuzzer reads them at startup. Can be run years apart. |
| HTTP layer | **`RequestUtilsProtocol`** | All network I/O goes through a protocol interface. Plugins can replace the entire HTTP implementation without touching core logic. |
| Chain strategies | **`BaseChainStrategy`** | `TopologicalChainStrategy` and `IDORChainStrategy` are swappable; adding a new traversal strategy requires no changes to `ChainGenerator`. |
| Detectors | **`Detector` abstract base** | All detectors share a uniform `detect()` interface. `DEngine` iterates a list — adding a new detector is a one-liner in `__init__.py`. |
| Materializers | **`Materializer` base class** | Payload generation strategies are interchangeable. `FEngine` selects the right materializer by type. |
| Programmatic API | **`core.py`** | Clean facade hiding the full compiler+fuzzer pipeline behind `compile_and_fuzz()`. |

---

### ⚠️ Tightly Coupled

| Coupling | Location | Impact |
|---|---|---|
| **`config.py` global module** | Imported directly by 50+ files | Any test that needs different config values must monkeypatch module-level variables. Impossible to run two configurations in the same process. |
| **`Stats` singleton** | Accessed via `Stats()` from detectors, fengine, fuzzer | Detectors cannot be unit-tested in isolation without the singleton accumulating state across tests. Stats can only be reset by calling `__init__` directly or reimporting the module. |
| **`plugins_handler.get_request_utils()`** | Called as a module-level function from compiler, fengine, detectors | The HTTP layer is a global service rather than an injected dependency. Mocking requires patching the module, not passing a mock. |
| **`API` reads disk at `__init__`** | `Fuzzer → API(url, save_path)` reads YAML immediately in constructor | Fuzzer construction fails if compiled files don't exist yet. No lazy loading. |
| **`ObjectsBucket` path from `config`** | Save/load path is always `config.OUTPUT_DIRECTORY / ...` | Cannot have two buckets for different outputs in the same process. |

---

## Data Flow Summary

```
Target GraphQL API
       │  ← HTTP introspection
       ▼
  Introspection JSON
       │  ← parse (7 parsers)
       ▼
  Raw YAML (objects / queries / mutations / …)
       │  ← resolve dependencies (heuristic + optional LLM)
       ▼
  Compiled YAML  +  dependency_graph.png
       │  ← graph traversal (topological + IDOR strategies)
       ▼
  chains.yaml
       │
  ─────┼─────── COMPILER DONE — FUZZER STARTS ────────────────
       │
       ▼
  Fuzzer reads: compiled YAML → API object
                chains.yaml   → list[Chain]
                DiGraph       → island-node discovery
       │
       ├── For each Chain:
       │     FEngine runs each ChainStep with its RuntimeProfile
       │     ObjectsBucket accumulates returned objects
       │     DEngine runs detectors per node
       │     IDORChainDetector analyses multi-profile results
       │
       ├── DEngine runs API-level detectors (introspection, field suggestions)
       │
       └── Stats.save() + ObjectsBucket.save() + detection_writer → files
              │
              ▼
       stats.txt · stats.json · logs/ · detections/ · objects_bucket.pkl
```

---

## Design Patterns in Use

| Pattern | Where | Notes |
|---|---|---|
| **Strategy** | `ChainGenerator` + `BaseChainStrategy` | `TopologicalChainStrategy` / `IDORChainStrategy` are swappable |
| **Template Method** | `Detector` abstract base | Subclasses implement `_is_vulnerable()` / `_is_potentially_vulnerable()`; base handles the rest |
| **Plugin / Protocol** | `plugins_handler` + `RequestUtilsProtocol` | Entire HTTP layer swappable at runtime |
| **Factory** | `DEngine` instantiates detector lists | Adding a detector is one line in `detectors/__init__.py` |
| **Singleton** | `Stats`, `FEngine`, `ObjectsBucket` | ⚠️ Makes parallelism and isolated testing difficult |
| **Facade** | `core.py` | Clean programmatic API hiding the full compiler+fuzzer pipeline |

---

## Recommendations

1. **Inject config** — pass a `Config` dataclass rather than importing the global module. Enables multiple concurrent configurations and eliminates monkeypatching in tests.
2. **Break the `Stats` singleton** — pass `Stats` as a constructor argument to `FEngine`, `DEngine`, and detectors. State would no longer leak between runs in the same process.
3. **Break the `FEngine` singleton** — `Fuzzer` already owns `FEngine`; the singleton decorator adds no value and prevents isolated unit tests.
4. **Lazy-load `API`** — reading all YAML in the constructor means `Fuzzer(path, url)` fails if compilation hasn't run yet. Lazy loading would give a clearer error message.
5. **Abstract storage** — introduce a `StorageBackend` interface so file paths aren't hard-coded via `config` throughout every component.
