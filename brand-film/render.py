#!/usr/bin/env python3
"""J-WALT brand film -- render pipeline CLI.

  python render.py linework                 export model edges for the wireframe layer
  python render.py stills [--preview]       Cycles projector stills (cached by content hash)
  python render.py frames -f 16x9 [--preview] [--start S --end E] [--workers N]
  python render.py audio                    score + sound design -> output/audio
  python render.py encode -f 16x9           frames + audio -> output/masters
  python render.py all [--preview]          everything, all formats

Times are film seconds. See README.md for the full workflow.
"""
from __future__ import annotations

import argparse
import multiprocessing as mp
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from jfilm import config  # noqa: E402


def cmd_linework(_args):
    from jfilm import scene as S
    from jfilm.scene import linework
    S.build_scene()
    config.CACHE.mkdir(parents=True, exist_ok=True)
    info = linework.export(str(config.LINEWORK))
    print("linework:", info)


def all_still_specs():
    from jfilm.render import stills as ST
    from jfilm.shots import base
    specs = list(ST.env_specs())
    seen = set()
    for sh in base.all_shots():
        for sp in sh.stills():
            if sp.name not in seen:
                specs.append(sp)
                seen.add(sp.name)
    return specs


def cmd_stills(args):
    from jfilm import scene as S
    from jfilm.render import stills as ST
    S.build_scene()
    specs = all_still_specs()
    if args.only:
        want = set(args.only.split(","))
        specs = [s for s in specs if s.name in want or any(s.name.startswith(w) for w in want)]
    todo = [s for s in specs if args.force or not ST.is_current(s, args.preview)]
    print(f"stills: {len(specs)} total, {len(todo)} to render ({'preview' if args.preview else 'final'})")
    for i, sp in enumerate(todo):
        t0 = time.time()
        ST.render(sp, preview=args.preview, force=True)
        print(f"  [{i + 1}/{len(todo)}] {sp.name}  {time.time() - t0:.0f}s", flush=True)


def _frame_worker(fmt_key, preview, frames, outdir, q):
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    from jfilm.render.frame import FrameRenderer, write_png
    cfg = config.load()
    fr = FrameRenderer(fmt_key, preview=preview)
    import traceback
    for i in frames:
        t = i / cfg.fps
        try:
            img = fr.render(t, i)
        except Exception:
            q.put(("error", i, traceback.format_exc()))
            return
        write_png(Path(outdir) / f"f_{i:04d}.png", img)
        q.put(i)


def frames_dir(fmt_key, preview):
    return config.FRAMES / f"{fmt_key}{'_preview' if preview else ''}"


def cmd_frames(args):
    cfg = config.load()
    fmts = list(cfg.formats) if args.format == "all" else args.format.split(",")
    for fk in fmts:
        out = frames_dir(fk, args.preview)
        out.mkdir(parents=True, exist_ok=True)
        a = int(round(args.start * cfg.fps))
        b = int(round((args.end if args.end is not None else cfg.duration) * cfg.fps))
        idx = list(range(a, b, args.every))
        if not args.force:
            idx = [i for i in idx if not (out / f"f_{i:04d}.png").exists()]
        print(f"frames {fk}: {len(idx)} to render -> {out}", flush=True)
        if not idx:
            continue
        n = max(1, min(args.workers, len(idx)))
        chunks = [idx[k::n] for k in range(n)]
        ctx = mp.get_context("spawn")
        q = ctx.Queue()
        procs = [ctx.Process(target=_frame_worker, args=(fk, args.preview, c, str(out), q)) for c in chunks]
        t0 = time.time()
        for p in procs:
            p.start()
        done = 0
        import queue
        while done < len(idx):
            try:
                msg = q.get(timeout=60)
            except queue.Empty:
                dead = [p for p in procs if not p.is_alive() and p.exitcode]
                if dead:
                    for p in procs:
                        p.terminate()
                    raise SystemExit(f"a frame worker died (exit {dead[0].exitcode}; out of memory?)")
                continue
            if isinstance(msg, tuple):
                for p in procs:
                    p.terminate()
                raise SystemExit(f"frame {msg[1]} failed:\n{msg[2]}")
            done += 1
            if done % 12 == 0 or done == len(idx):
                el = time.time() - t0
                print(f"  {fk}: {done}/{len(idx)}  {el / done:.1f}s/frame  eta {el / done * (len(idx) - done) / 60:.1f} min",
                      flush=True)
        for p in procs:
            p.join()
            if p.exitcode:
                raise SystemExit(f"worker failed ({p.exitcode})")


def cmd_audio(args):
    from jfilm.audio import mix
    mix.render_all()


def cmd_encode(args):
    from jfilm import encode
    cfg = config.load()
    fmts = list(cfg.formats) if args.format == "all" else args.format.split(",")
    for fk in fmts:
        encode.encode(fk, frames_dir(fk, args.preview), preview=args.preview)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("linework")
    s = sub.add_parser("stills")
    s.add_argument("--preview", action="store_true")
    s.add_argument("--force", action="store_true")
    s.add_argument("--only", default="")
    f = sub.add_parser("frames")
    f.add_argument("-f", "--format", default="16x9")
    f.add_argument("--preview", action="store_true")
    f.add_argument("--force", action="store_true")
    f.add_argument("--start", type=float, default=0.0)
    f.add_argument("--end", type=float, default=None)
    f.add_argument("--every", type=int, default=1)
    f.add_argument("--workers", type=int, default=3)
    sub.add_parser("audio")
    e = sub.add_parser("encode")
    e.add_argument("-f", "--format", default="16x9")
    e.add_argument("--preview", action="store_true")
    a = sub.add_parser("all")
    a.add_argument("--preview", action="store_true")
    args = ap.parse_args()
    if args.cmd == "all":
        cmd_linework(args)
        cmd_stills(argparse.Namespace(preview=args.preview, force=False, only=""))
        cmd_audio(args)
        for fk in config.load().formats:
            cmd_frames(argparse.Namespace(format=fk, preview=args.preview, force=False, start=0.0, end=None, every=1,
                                          workers=3))
            cmd_encode(argparse.Namespace(format=fk, preview=args.preview))
        return
    {"linework": cmd_linework, "stills": cmd_stills, "frames": cmd_frames, "audio": cmd_audio,
     "encode": cmd_encode}[args.cmd](args)


if __name__ == "__main__":
    main()
