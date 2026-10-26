# MyPvZ module workflow

- First read `docs/STATUS.md`, `docs/HANDOFF.md`, and the requested row in `docs/PLAN.md`. Read architecture/rules only as needed; do not reread all historic logs.
- Execute only the module explicitly requested by the user. Do not advance automatically to the next module. M00 excludes gameplay, original-asset import, cook, and packaging.
- User selected GPT-6.1 Sol with Ultra reasoning. Preserve that model; keep delegated work narrowly scoped and account for shared usage.
- Engine is pinned to UE 5.8.2. Use C++ core, Paper 2D presentation, UMG UI, and Blueprint-exposed configuration. Use this installed engine's templates/headers to verify APIs.
- Preserve the original sibling `../protptype` directory. It is reference material, not a build dependency. Missing/uncertain original behavior is recorded in `docs/RULES.md`, not claimed as verified.
- Compile with the project editor closed. Save commands and concise evidence. Do not mark work complete solely because source files exist or Live Coding succeeded.
- Avoid checking in generated Binaries, Intermediate, Saved, DDC, local machine secrets, large build outputs, or bundled Microsoft debug runtime DLLs. Commit source/configuration, required map/assets, scripts, and concise handoff records.
- At each module's end update STATUS, HANDOFF, and its validation record with actual results, remaining limitations, and next entry point. Unfinished checks must stay explicitly unfinished.
- If quota or an external dependency prevents completion, preserve the last verified checkpoint and exact remaining work. Do not silently change the module's completion criteria.
- Keep handoffs short and self-contained so the next module can run in a new chat. Preserve relevant existing repository content and avoid force-pushing.
