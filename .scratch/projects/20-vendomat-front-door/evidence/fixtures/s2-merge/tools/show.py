import json,sys
types=sys.argv[1:] or "str int bool enum lstr lpkg astr sub nul lines sep pkg".split()
for t in types:
    d=json.load(open(f"logs/matrix-{t}.json"))
    print("==",t)
    Ls=sorted({k.split("_")[0][1:] for k in d}, key=lambda x:"0pdfba".index(x))
    Gs=["0","p","o100","o90","o75","o60","d","f"]
    for U in ["0","p","f"]:
        print(" U="+U)
        print("  %-4s"%"L\\G"+"".join("%-24s"%g for g in Gs))
        for L in Ls:
            row=[]
            for G in Gs:
                v=d.get(f"L{L}_G{G}_U{U}","-")
                s=json.dumps(v,separators=(",",":")) if v!="ERROR" else "ERR"
                row.append("%-24s"%s[:23])
            print("  %-4s"%L+"".join(row))
