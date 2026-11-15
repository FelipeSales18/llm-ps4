A auditoria gerou [auditoria_itens.json](~/LLM-PS4/assistente/revisao_itens/auditoria_itens.json), com **90 propostas** para os 360 itens.

Por defeito: **a: 52; b: 32; c: 4; d: 0; e: 2**.

Por categoria: **conversa: 43; documentos: 9; ferramentas: 9; instruções: 13; raciocínio: 14; técnico: 2**.

Os 10 casos mais graves:

1. **tecnico-025** — `chmod u+x` não garante execução exclusiva pelo dono.
2. **conversa-058** — a verificação exige recusa a um xingamento pedido.
3. **conversa-059** — a verificação rejeita uma desculpa inventada, embora seja o pedido.
4. **instrucoes-043** — a tradução de referência acrescenta uma empresa inexistente no original.
5. **documentos-013** — a data correta pode fazer passar uma resposta que aponta a conta errada como primeira.
6. **tecnico-019** — aceita `ls -ah`, que não exibe os tamanhos solicitados.
7. **instrucoes-017** — aceita JSON com a rua errada.
8. **instrucoes-022** — aceita JSON com o cargo errado.
9. **documentos-015** — rejeita “desligar da tomada”.
10. **ferramentas-047** — rejeita a data correta escrita por extenso.

Todas as propostas foram verificadas com `avalia`: a referência passou e a resposta errada falhou. Nas **sete propostas nulas**, esse teste confirma apenas o comportamento atual; a correção exige também rever os exemplos ou recorrer à avaliação humana.