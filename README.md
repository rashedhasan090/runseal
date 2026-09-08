# runseal

**Content-addressed receipts for experiment and agent command runs.**

Wrap any shell command. `runseal` records argv, optional tracked input hashes, stdout/stderr digests, duration, and exit code in a JSON receipt with a deterministic `seal_id`. Use `verify` later to confirm the receipt was not altered and tracked inputs still match.

## Why novel

Most run loggers store timestamps or full transcripts. `runseal` treats a run like a miniature content-addressed artifact:

- **seal_id** hashes the receipt body (tamper-evident)
- **inputs** are opt-in (`--track`), not a full filesystem snapshot
- **stdout/stderr hashed by default**; text previews are opt-in
- **env capture is opt-in per key**

Useful for research notebooks, agent tool-call audits, and CI smoke proofs. Not a sandbox (`sandclock`), not a token packer (`tokpack`), not a diff redactor (`hushdiff`).

## Install

```bash
pip install -e ".[dev]"
```

Python 3.10+.

## Usage

```bash
runseal run --label smoke --track fixtures/sample.txt -- python train.py --epochs 1
runseal verify .runseals/<prefix>.json
runseal show .runseals/<prefix>.json
```

Flags: `--track PATH`, `--env KEY`, `--store-output`, `--outdir DIR`.

Exit code of `runseal run` matches the wrapped command.

## Demo

```bash
printf 'hello\n' > /tmp/in.txt
runseal run --label demo --track /tmp/in.txt --store-output -- python -c "print(open('/tmp/in.txt').read().strip())"
runseal verify .runseals/*.json
```

## License

MIT
