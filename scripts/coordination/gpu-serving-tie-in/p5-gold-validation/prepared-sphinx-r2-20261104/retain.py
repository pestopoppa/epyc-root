import pathlib,sys,shutil
p=pathlib.Path(sys.argv[1]);dest=pathlib.Path(sys.argv[2])
for x in p.iterdir():
 if x.is_file() and (x.suffix in ('.py','.json','.sh','.md') or x.name in ['SOURCE.sha256','.dockerignore','Dockerfile','KEEP','PREPARATION_READY','build.log']):shutil.copyfile(x,dest/x.name)
