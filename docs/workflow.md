# Workflow

## Graph

```mermaid
flowchart LR
    S([START]) --> O[generate_outline]
    O --> T[generate_transcript]
    T --> A[generate_all_audio]
    A --> C[combine_audio]
    C --> E([END])
```

## Sequence (high level)

```mermaid
sequenceDiagram
    participant U as UserOrUI
    participant W as create_podcast
    participant G as LangGraph
    participant L as LLM
    participant T as TTS
    U->>W: content briefing episode_name output_dir episode_profile
    W->>W: load episode resolve speakers
    W->>G: ainvoke initial state
    G->>L: structured outline
    G->>L: structured transcript per segment
    G->>T: synthesize clips batched
    G->>G: pydub combine mp3
    G-->>W: final path + artifacts
```

## Artifacts

Given the **`output_dir`** you pass to `create_podcast` (e.g. `output/my_episode`), the pipeline writes:

- `{output_dir}/outline.json`
- `{output_dir}/transcript.json`
- `{output_dir}/clips/*.mp3` (per line / clip)
- `{output_dir}/audio/{episode_name}.mp3` (final mix)
