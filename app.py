from flask import Flask, request, jsonify, render_template_string
import random

app = Flask(__name__)

# Probabilidades de SUCESSO (subir do nível atual para o próximo)
PROBS = {
    "imortal": {1: 0.50, 2: 0.30, 3: 0.30, 4: 0.30, 5: 0.30, 6: 0.30, 7: 0.30, 8: 0.30},
    "ceu":     {1: 0.65, 2: 0.45, 3: 0.45, 4: 0.45, 5: 0.45, 6: 0.45, 7: 0.45, 8: 0.45},
    "maligna": {1: 0.533,2: 0.335,3: 0.335,4: 0.335,5: 0.335,6: 0.335,7: 0.335,8: 0.335},
    "terra":   {1: 1.00, 2: 0.25, 3: 0.10, 4: 0.04, 5: 0.02, 6: 0.0077, 7: 0.0047, 8: 0.0025},
}

# Regras de FALHA por pedra:
# 'stay' = mantém | 'drop' = -1 nível | 'reset' = volta para +0
FAIL_RULE = {
    "imortal": "reset",
    "ceu":     "reset",
    "maligna": "drop",
    "terra":   "stay",
}

MAX_LEVEL = 8

TEMPLATE = """
<!doctype html>
<html lang="pt-br">
  <head>
    <meta charset="utf-8"/>
    <title>PW · Simulador de Refino The Classic PW 1.2.6</title>
    <meta name="viewport" content="width=device-width, initial-scale=1"/>
    <style>
      :root { --b:#e5e7eb; --muted:#6b7280; --ok:#065f46; --bad:#b91c1c; --sel:#1d4ed8; }
      *{box-sizing:border-box}
      body{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;margin:1.2rem;background:#f8fafc}
      h1{margin:.2rem 0 .4rem}
      .grid{display:grid;gap:1rem;grid-template-columns:340px 1fr}
      .card{background:#fff;border:1px solid var(--b);border-radius:.8rem;padding:1rem}
      .muted{color:var(--muted)}
      .row{display:grid;grid-template-columns:1fr 1fr;gap:.6rem}
      input,button{padding:.55rem .65rem;font-size:1rem}
      input{width:100%}
      table{border-collapse:collapse;width:100%}
      th,td{border-bottom:1px solid #f1f5f9;padding:.4rem .25rem;text-align:left}
      .total{font-weight:700}
      .inv{display:grid;grid-template-columns:repeat(3,1fr);gap:.6rem}
      .slot{border:2px dashed #cbd5e1;border-radius:.75rem;padding:1rem;height:120px;display:flex;align-items:center;justify-content:center;background:#f9fafb}
      .slot.over{background:#eef2ff;border-color:#6366f1}
      .chip{display:inline-flex;align-items:center;gap:.35rem;border:1px solid #e5e7eb;border-radius:999px;padding:.15rem .5rem}
      .lvl{font-weight:800}
      .item{border:1px solid #e5e7eb;border-radius:.6rem;padding:.6rem;background:#ffffff;cursor:grab}
      .item.drag{opacity:.6}
      .log{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:.92rem;background:#fbfbfb;border:1px solid #e5e7eb;border-radius:.5rem;max-height:220px;overflow:auto;padding:.5rem}
      .ok{color:var(--ok)} .bad{color:var(--bad)}
      .toolbar{display:flex;gap:.5rem;flex-wrap:wrap}

      /* Bolinhas clicáveis das pedras */
      .stones { display:flex; gap:.75rem; align-items:center; flex-wrap:wrap; }
      .stone { display:flex; flex-direction:column; align-items:center; gap:.3rem; cursor:pointer; }
      .stone .dot { width:46px; height:46px; border-radius:999px; border:2px solid #cbd5e1; background:#ffffff; display:flex; align-items:center; justify-content:center; font-weight:700; }
      .stone.selected .dot { border-color: var(--sel); box-shadow: 0 0 0 3px rgba(29,78,216,.15); }
      .stone .label { font-size:.9rem; color:#111; }
      .stone[data-stone="imortal"] .dot { background:#fff7ed }  /* leve laranja */
      .stone[data-stone="ceu"]     .dot { background:#eff6ff }  /* leve azul */
      .stone[data-stone="maligna"] .dot { background:#fdf2f8 }  /* leve rosa */
      .stone[data-stone="terra"]   .dot { background:#ecfdf5 }  /* leve verde */
      .actions{display:flex; gap:.5rem; flex-wrap:wrap}
      button{cursor:pointer}
      code{background:#f1f5f9;border:1px solid #e5e7eb;border-radius:.25rem;padding:.1rem .25rem}
      .section-title{display:flex;align-items:center;justify-content:space-between;gap:.5rem}
    </style>
  </head>
  <body>
    <h1>Simulador de Refino The Classic PW 1.2.6</h1>
    <p class="muted">Arraste um item do inventário para a mesa, escolha a pedra clicando numa <b>bolinha</b> e clique <b>Refinar</b>. O nível fica salvo no <u>item</u>.</p>

    <div class="grid">
      <!-- Lado esquerdo: preços, totais, probabilidades -->
      <div class="card">
        <div class="section-title">
          <h3>Preços das pedras</h3>
          <div class="toolbar">
            <button id="save-prices">Salvar preços</button>
            <button id="reset-all" title="Zera níveis, custos, quantidades e limpa a mesa/log">Resetar tudo</button>
          </div>
        </div>

        <div class="row">
          <div><label for="p_imortal">Pedra Imortal</label><input id="p_imortal" type="number" step="0.0001" value="0.30"></div>
          <div><label for="p_ceu">Pedra Céu</label><input id="p_ceu" type="number" step="0.0001" value="0.45"></div>
        </div>
        <div class="row" style="margin-top:.4rem">
          <div><label for="p_maligna">Pedra Maligna</label><input id="p_maligna" type="number" step="0.0001" value="0.33"></div>
          <div><label for="p_terra">Pedra Céu & Terra</label><input id="p_terra" type="number" step="0.0001" value="1.00"></div>
        </div>

        <h3 style="margin-top:1rem">Totais (custos)</h3>
        <table>
          <tr><th>Pedra Imortal</th><td id="c_imortal">0</td></tr>
          <tr><th>Pedra Céu</th><td id="c_ceu">0</td></tr>
          <tr><th>Pedra Maligna</th><td id="c_maligna">0</td></tr>
          <tr><th>Pedra Céu & Terra</th><td id="c_terra">0</td></tr>
          <tr><th class="total">TOTAL</th><td class="total" id="c_total">0</td></tr>
        </table>

        <h3 style="margin-top:1rem">Quantidade de pedras utilizadas</h3>
        <table>
          <tr><th>Pedra Imortal</th><td id="u_imortal">0</td></tr>
          <tr><th>Pedra Céu</th><td id="u_ceu">0</td></tr>
          <tr><th>Pedra Maligna</th><td id="u_maligna">0</td></tr>
          <tr><th>Pedra Céu & Terra</th><td id="u_terra">0</td></tr>
          <tr><th class="total">TOTAL</th><td class="total" id="u_total">0</td></tr>
        </table>

        <h3 style="margin-top:1rem">Probabilidades</h3>
        <p class="muted small">Sucesso para subir do nível atual para o próximo (+1..+8). Regras de falha:
          <span class="chip">Pedra Imortal: zera</span>
          <span class="chip">Pedra Céu: zera</span>
          <span class="chip">Pedra Maligna: -1</span>
          <span class="chip">Pedra Céu & Terra: mantém</span>
        </p>
        <div id="probs"></div>
      </div>

      <!-- Lado direito: inventário + mesa -->
      <div>
        <div class="card" style="margin-bottom:1rem">
          <h3>Inventário</h3>
          <div id="inventory" class="inv"></div>
        </div>

        <div class="card">
          <h3>Simulador de Refino The Classic PW 1.2.6</h3>
          <div id="table-slot" class="slot" data-slot>Arraste um item aqui</div>

          <div style="margin-top:.8rem">
            <label>Escolha a pedra</label>
            <div id="stones" class="stones">
              <div class="stone selected" data-stone="imortal" tabindex="0">
                <div class="dot">IM</div><div class="label">Pedra Imortal</div>
              </div>
              <div class="stone" data-stone="ceu" tabindex="0">
                <div class="dot">CE</div><div class="label">Pedra Céu</div>
              </div>
              <div class="stone" data-stone="maligna" tabindex="0">
                <div class="dot">MA</div><div class="label">Pedra Maligna</div>
              </div>
              <div class="stone" data-stone="terra" tabindex="0">
                <div class="dot">TE</div><div class="label">Pedra Céu & Terra</div>
              </div>
            </div>
          </div>

          <div class="actions" style="margin-top:.8rem">
            <button id="refine">Refinar</button>
            <button id="refine10">Refinar x10</button>
            <button id="remove">Remover da mesa</button>
          </div>

          <div class="log" id="log" style="margin-top:.6rem"></div>
        </div>
      </div>
    </div>

    <script>
      const MAX_LEVEL = {{max_level}};
      const pricesInputs = {
        imortal: document.getElementById('p_imortal'),
        ceu: document.getElementById('p_ceu'),
        maligna: document.getElementById('p_maligna'),
        terra: document.getElementById('p_terra'),
      };

      // Estado: 3 itens no inventário, nível fica no item
      const state = {
        items: [
          {id:'A', name:'Espada', lvl:0},
          {id:'B', name:'Peitoral', lvl:0},
          {id:'C', name:'Elmo', lvl:0},
        ],
        onTable: null, // id do item na mesa
        spent: {imortal:0, ceu:0, maligna:0, terra:0},
        used:  {imortal:0, ceu:0, maligna:0, terra:0},
        selectedStone: 'imortal',
      };

      // Helpers UI
      const $inv = document.getElementById('inventory');
      const $slot = document.getElementById('table-slot');
      const $log  = document.getElementById('log');
      const $stones = document.getElementById('stones');

      function fmt(n){ return String(Number(n).toFixed(4)).replace(/\\.0+$/, ""); }
      function priceOf(stone){ return Number(pricesInputs[stone].value || 0); }

      function updateCostsUI(){
        const t = state.spent.imortal + state.spent.ceu + state.spent.maligna + state.spent.terra;
        document.getElementById('c_imortal').textContent = fmt(state.spent.imortal);
        document.getElementById('c_ceu').textContent     = fmt(state.spent.ceu);
        document.getElementById('c_maligna').textContent = fmt(state.spent.maligna);
        document.getElementById('c_terra').textContent   = fmt(state.spent.terra);
        document.getElementById('c_total').textContent   = fmt(t);
      }

      function updateUsageUI(){
        const totalUsed = state.used.imortal + state.used.ceu + state.used.maligna + state.used.terra;
        document.getElementById('u_imortal').textContent = state.used.imortal;
        document.getElementById('u_ceu').textContent     = state.used.ceu;
        document.getElementById('u_maligna').textContent = state.used.maligna;
        document.getElementById('u_terra').textContent   = state.used.terra;
        document.getElementById('u_total').textContent   = totalUsed;
      }

      // Persistência de preços
      (function loadPrices(){
        const saved = JSON.parse(localStorage.getItem('pw_refino_prices') || '{}');
        for (const k of Object.keys(pricesInputs)) if (saved[k]!=null) pricesInputs[k].value = saved[k];
        updateCostsUI();
        updateUsageUI();
      })();
      document.getElementById('save-prices').onclick = () => {
        const toSave = {}; for (const k of Object.keys(pricesInputs)) toSave[k] = Number(pricesInputs[k].value||0);
        localStorage.setItem('pw_refino_prices', JSON.stringify(toSave));
      };

      // Resetar tudo: níveis, custos, quantidades, mesa e log
      document.getElementById('reset-all').onclick = () => {
        state.items = state.items.map(it => ({...it, lvl:0}));
        state.spent = {imortal:0, ceu:0, maligna:0, terra:0};
        state.used  = {imortal:0, ceu:0, maligna:0, terra:0};
        state.onTable = null;
        renderInventory();
        updateCostsUI();
        updateUsageUI();
        $slot.textContent = 'Arraste um item aqui';
        $log.textContent = '';
        // Mantém preços configurados; se quiser zerar os campos também, basta descomentar:
        // for (const k of Object.keys(pricesInputs)) pricesInputs[k].value = 0;
      };

      // INVENTÁRIO (draggable)
      function renderInventory(){
        $inv.innerHTML = '';
        state.items.forEach(it => {
          const card = document.createElement('div');
          card.className = 'item';
          card.draggable = true;
          card.dataset.id = it.id;
          card.innerHTML = '<div style="display:flex;justify-content:space-between;align-items:center;">'
            + `<strong>${it.name}</strong>`
            + `<span class="chip lvl">+${it.lvl}</span>`
            + '</div>';
          card.addEventListener('dragstart', e => { card.classList.add('drag'); e.dataTransfer.setData('text/plain', it.id); });
          card.addEventListener('dragend',   () => card.classList.remove('drag'));
          $inv.appendChild(card);
        });
      }
      renderInventory();

      // MESA (drop target)
      $slot.addEventListener('dragover', e => { e.preventDefault(); $slot.classList.add('over'); });
      $slot.addEventListener('dragleave', () => $slot.classList.remove('over'));
      $slot.addEventListener('drop', e => {
        e.preventDefault(); $slot.classList.remove('over');
        const id = e.dataTransfer.getData('text/plain');
        placeOnTable(id);
      });

      function placeOnTable(id){
        const it = state.items.find(x=>x.id===id);
        if (!it) return;
        state.onTable = id;
        $slot.innerHTML = `<div><strong>${it.name}</strong> <span class="chip">Nível atual: <b>+${it.lvl}</b></span></div>`;
      }

      document.getElementById('remove').onclick = () => {
        state.onTable = null;
        $slot.textContent = 'Arraste um item aqui';
      };

      // Seleção de pedra (bolinhas)
      $stones.addEventListener('click', (e) => {
        const stoneEl = e.target.closest('.stone');
        if (!stoneEl) return;
        document.querySelectorAll('.stone').forEach(el => el.classList.remove('selected'));
        stoneEl.classList.add('selected');
        state.selectedStone = stoneEl.dataset.stone;
      });

      // Refinar tentativa (consome preço, chama backend)
      async function refineOnce(){
        if (!state.onTable){ log('Selecione um item na mesa.', 'bad'); return; }
        const it = state.items.find(x=>x.id===state.onTable);
        if (it.lvl >= MAX_LEVEL){ log(`Item já está no nível máximo (+${MAX_LEVEL}).`, 'ok'); return; }

        const stone = state.selectedStone;
        state.spent[stone] += priceOf(stone);
        state.used[stone] += 1;
        updateCostsUI();
        updateUsageUI();

        const res = await fetch('/api/attempt', {
          method:'POST', headers:{'Content-Type':'application/json'},
          body: JSON.stringify({ level: it.lvl, stone })
        }).then(r=>r.json());

        it.lvl = res.new_level;
        renderInventory();          // nível visível no inventário
        placeOnTable(it.id);        // atualiza nível exibido na mesa

        // Mensagens padronizadas (EN)
        if (res.success) {
          log('Refinado com sucesso!', 'ok');
        } else {
          let msg = 'Refining failed.';
          if (res.applied_rule === 'reset')      msg += ' Item level reset.';
          else if (res.applied_rule === 'stay')  msg += ' Item level unchanged.';
          else if (res.applied_rule === 'drop')  msg += ' Item level decreased.';
          log(msg, 'bad');
        }
      }

      document.getElementById('refine').onclick  = () => refineOnce();
      document.getElementById('refine10').onclick = async () => { for (let i=0;i<10;i++) await refineOnce(); };

      function log(msg, cls){
        const line = document.createElement('div');
        if (cls) line.classList.add(cls);
        line.textContent = msg;
        $log.prepend(line);
      }

      // Tabela de probabilidades
      fetch('/api/probs').then(r=>r.json()).then(data=>{
        const host = document.getElementById('probs');
        const tbl = document.createElement('table');
        const head = document.createElement('tr');
        head.innerHTML = '<th>+Nível</th>' + Object.keys(data).map(k=>`<th>${({
          imortal:"Pedra Imortal", ceu:"Pedra Céu", maligna:"Pedra Maligna", terra:"Pedra Céu & Terra"
        })[k]}</th>`).join('');
        tbl.appendChild(head);
        for (let lvl=1; lvl<= {{max_level}}; lvl++){
          const tr = document.createElement('tr');
          tr.innerHTML = `<td>+${lvl}</td>` + Object.keys(data).map(k=>{
            const v = (data[k][lvl]*100).toFixed(3)+'%';
            return `<td>${v}</td>`;
          }).join('');
          tbl.appendChild(tr);
        }
        host.appendChild(tbl);
      });
    </script>
  </body>
</html>
"""

def attempt_once(current_level: int, stone: str):
    """Executa UMA tentativa de refino do nível atual com a 'stone'."""
    if current_level >= MAX_LEVEL:
        return {"success": False, "new_level": current_level, "p_succ": 0.0, "roll": 1.0, "applied_rule": "max"}

    next_lvl = current_level + 1
    p = PROBS[stone][next_lvl]
    roll = random.random()
    success = roll < p

    if success:
        new_level = current_level + 1
        rule = "success"
    else:
        rule = FAIL_RULE[stone]
        if rule == "drop":
            new_level = max(0, current_level - 1)
        elif rule == "reset":
            new_level = 0
        else:  # stay
            new_level = current_level

    return {"success": success, "new_level": new_level, "p_succ": p, "roll": roll, "applied_rule": rule}

@app.route("/")
def index():
    return render_template_string(TEMPLATE, max_level=MAX_LEVEL)

@app.route("/api/attempt", methods=["POST"])
def api_attempt():
    data = request.get_json(force=True)
    level = int(data.get("level", 0))
    stone = data.get("stone", "imortal")
    if stone not in PROBS:
        return jsonify({"error":"stone inválida"}), 400
    return jsonify(attempt_once(level, stone))

@app.route("/api/probs")
def api_probs():
    return jsonify(PROBS)

if __name__ == "__main__":
    # http://127.0.0.1:5000
    app.run(debug=True)
