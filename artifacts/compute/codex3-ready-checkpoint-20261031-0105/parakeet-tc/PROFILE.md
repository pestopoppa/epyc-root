# Parakeet v3 transcribe validation execution profile

The full 1,437-clip FLEURS validation population is collected with the pinned transcribe.cpp Parakeet v3 Q8 and F16 models, model-native automatic language output, canonical 30-second chunking and complete emitted-token witnesses. Inputs are partitioned by manifest index across eight disjoint three-CPU workers in a 24-CPU quarter with 32 GiB correctness reservation. Native cases have a 600-second timeout and a 620-second no-new-case reserve; STOP drains workers and preserves exposures. The identical dispatcher uses two one-CPU workers on duplicate diagnostic JFK inputs for R11, each executing both model settings. No validation scoring, test exposure or auxiliary language-identification model is part of collection.

Completed empty transcripts count as full deletions; zero native tokens require the explicit completion count marker. Otherwise token and UNK counts remain unknown.
