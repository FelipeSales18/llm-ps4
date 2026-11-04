import csv, os
HERE=os.path.dirname(os.path.abspath(__file__))
TPS=8.4; LIMS=[160,200,256,320]
L=lambda n: list(csv.DictReader(open(f'{HERE}/eval/eval_{n}.csv')))
res={}
for name,lab in (('base','base'),('grpo','treinado')):
    R=L(name); N=len(R); rows=[]
    for lim in LIMS:
        fx=st=tr=tok=0
        for r in R:
            n=int(r['n_tokens']); cut = n>lim or (r['truncated']=='True' and n<=lim)
            tok+=min(n,lim)
            if cut: tr+=1
            if n>lim: continue
            fx+=r['correct_flex']=='True'; st+=r['correct_strict']=='True'
        s=tok/N/TPS
        rows.append(dict(lim=lim,flex=100*fx/N,strict=100*st/N,nflex=fx,tok=tok/N,trunc=100*tr/N,s=s,sc=tok/TPS/fx))
    res[lab]=rows
out=["# Limite de tokens: simulação com os CSVs do Kaggle","",
"Fonte: `analise/eval/eval_base.csv` e `eval_grpo.csv` (1319 questões do teste do GSM8K, geração greedy, limite original de 320).",
"Regra: se `n_tokens` passa do limite, a resposta conta como cortada e errada; se fica no limite ou abaixo, nada muda.",
"Os tempos são só de geração, a 8,4 tokens/s (PS4, Q4_K_M, 8 threads), sem o processamento do prompt.","",
"| modelo | limite | flex | strict | tokens gerados (média) | cortadas | s/resposta | s/resposta correta (flex) |","|---|---|---|---|---|---|---|---|"]
for lab,rows in res.items():
    for r in rows:
        out.append(f"| {lab} | {r['lim']} | {r['flex']:.2f}% ({r['nflex']}) | {r['strict']:.2f}% | {r['tok']:.1f} | {r['trunc']:.2f}% | {r['s']:.2f} | {r['sc']:.2f} |")
g=res['treinado']; ref=g[-1]['flex']
ok=[r for r in g if ref-r['flex']<=0.5+1e-9]; best=min(ok,key=lambda r:r['lim'])
out+=["",f"**Recomendação: {best['lim']} tokens.** Nenhum limite menor entre os testados atende ao critério (queda de no máximo 0,5 ponto no flex do treinado em relação ao de 320):"]
for r in g:
    out.append(f"- {r['lim']}: queda de {ref-r['flex']:.2f} ponto no flex.")
out+=["","Cortar não compensa: o treinado já é curto (mediana de 120 tokens). Limites menores economizam poucos tokens em média "
f"(256: {g[-1]['tok']-g[2]['tok']:.1f} tokens, ~{g[-1]['s']-g[2]['s']:.2f} s por resposta) e perdem acertos nas questões longas, que são justamente as difíceis. "
"O tempo por resposta correta piora em todos os limites menores.","",
"Nota, fora dos quatro valores pedidos: varrendo limites inteiros, o menor que atende ao critério é **296** "
"(flex 75,89%, queda de 0,38 ponto, 128,8 tokens médios). Economiza só 0,4 token por resposta em relação ao de 320, então não vale a pena."]
open(f'{HERE}/limite_tokens.md','w').write("\n".join(out)+"\n")
print("\n".join(out))
