"""Apply supabase/migrations/*.sql in order through the management API; records applied files in table _anees_migrations."""
import sys, io
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import db

ROOT = Path(__file__).resolve().parent.parent
MIG = ROOT / 'supabase' / 'migrations'


def main(force=False):
    db.sql('create table if not exists _anees_migrations(name text primary key, applied_at timestamptz default now())')
    done = {r['name'] for r in db.sql('select name from _anees_migrations')}
    for p in sorted(MIG.glob('*.sql')):
        if p.name in done and not force:
            print('skip', p.name); continue
        db.sql(io.open(p, encoding='utf-8').read())
        db.sql(f"insert into _anees_migrations(name) values ('{p.name}') on conflict do nothing")
        print('applied', p.name)


if __name__ == '__main__':
    main(force='--force' in sys.argv)
