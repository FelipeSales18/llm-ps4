import csv, re, statistics, os, json
from math import comb
from tokenizers import Tokenizer
HERE=os.path.dirname(os.path.abspath(__file__))
TOK=Tokenizer.from_file(os.path.expanduser("~/LLM-PS4/gguf/hf/qwen3-1.7b-gsm8k-grpo/tokenizer.json"))
nt=lambda s: len(TOK.encode(s, add_special_tokens=False).ids) if s else 0
L=lambda n:{int(r['idx']):r for r in csv.DictReader(open(f'{HERE}/eval/eval_{n}.csv'))}
B,G=L('base'),L('grpo')
OP=re.compile(r"[=+×*/÷^]|\\times|\\div|\\frac|(?<=\d)\s*-\s*(?=\d)")
res={}
for name,D in (('base',B),('grpo',G)):
    data_tok=fmt_tok=tot=0; recheck=0; recheck_ids=[]
    for i,r in D.items():
        o=r['output']; q=r['question'].replace(',','')
        tot+=int(r['n_tokens'])
        qnums=set(re.findall(r"\d+(?:\.\d+)?", q))
        for l in o.splitlines():
            s=l.strip()
            nums=re.findall(r"\d+(?:\.\d+)?", s.replace(',',''))
            if nums and not s.startswith('####') and not OP.search(s) and all(n in qnums for n in nums):
                data_tok+=nt(l+"\n")
        # formatação: linhas só com $$, marcadores ** , \text{...} e $ isolados
        fmt_tok+=nt("\n".join(l for l in o.splitlines() if l.strip()=='$$'))
        fmt_tok+=2*o.count('**')//2
        fmt_tok+=sum(nt(m)-nt(m[6:-1]) for m in re.findall(r"\\text\{[^}]*\}", o))
        if re.search(r"recheck|re-?check|mistake|not possible|impossible|not an integer|Wait", o, re.I):
            recheck+=1; recheck_ids.append(i)
    acc=sum(D[i]['correct_flex']=='True' for i in recheck_ids)
    res[name]={'tok_listagem_dados_por_resp':round(data_tok/len(D),1),'pct_listagem':round(100*data_tok/tot,1),
               'tok_formatacao_por_resp':round(fmt_tok/len(D),1),'pct_formatacao':round(100*fmt_tok/tot,1),
               'resp_com_recheck':recheck,'acc_flex_recheck':round(acc/max(1,recheck),3),
               'tok_medios_recheck':round(statistics.mean(int(D[i]['n_tokens']) for i in recheck_ids),1) if recheck_ids else None,
               'trunc_entre_recheck':sum(D[i]['truncated']=='True' for i in recheck_ids)}
# Fisher bicaudal para "dinheiro" nas trocas
fl=json.load(open(f'{HERE}/flips_idx.json'))
kw=re.compile(r"\$|dollar|cents?\b|price|cost|pay|earn",re.I)
a=sum(bool(kw.search(G[i]['question'])) for i in fl['base_ok_grpo_erro']); n1=len(fl['base_ok_grpo_erro'])
c=sum(bool(kw.search(G[i]['question'])) for i in fl['base_erro_grpo_ok']); n2=len(fl['base_erro_grpo_ok'])
K=a+c; N=n1+n2
p=lambda x: comb(n1,x)*comb(n2,K-x)/comb(N,K)
p0=p(a); pf=sum(p(x) for x in range(max(0,K-n2),min(K,n1)+1) if p(x)<=p0+1e-12)
res['fisher_dinheiro']={'base_ok_grpo_erro':f'{a}/{n1}','base_erro_grpo_ok':f'{c}/{n2}','p_bicaudal':round(pf,4)}
# nas trocas para pior: o grpo deixou de escrever número? formato?
res['grpo_sem_####_nas_83']=sum(not re.search(r"####\s*-?\$?\d",G[i]['output']) for i in fl['base_ok_grpo_erro'])
res['base_strict_ok_nas_83']=sum(B[i]['correct_strict']=='True' for i in fl['base_ok_grpo_erro'])
print(json.dumps(res,indent=1,ensure_ascii=False))
json.dump(res,open(f'{HERE}/extra_dados.json','w'),indent=1,ensure_ascii=False)
