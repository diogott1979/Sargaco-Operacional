(function () { 'use strict';
function init(){
  // SARGACO-20261028-v3: classificação marítima e versão explícita do módulo.

  if(!window.map||!window.ol){document.getElementById('feedback').textContent='Não foi possível iniciar o mapa. Confirme os ficheiros e volte a carregar.';return;}
  const m=window.map, $=id=>document.getElementById(id), projection=m.getView().getProjection().getCode();
  const refs=[{key:'port',name:'Área portuária',layer:window.lyr_Areas_Portuarias_RAM_1,field:'Name'}, {key:'balneares',name:'Água balnear',layer:window.lyr_DRAAC_AguasBalneares_4,field:'Nome da Á'}, {key:'ifcn',name:'Área IFCN',layer:window.lyr_IFCN_3,field:'layer'}, {key:'municipios',name:'Município',layer:window.lyr_Madeira_Municipios_CAOP2023_2,field:'Municipio'}];
  const points=new ol.source.Vector(); const markerLayer=new ol.layer.Vector({source:points,style:new ol.style.Style({image:new ol.style.Circle({radius:8,fill:new ol.style.Fill({color:'#0c789e'}),stroke:new ol.style.Stroke({color:'#fff',width:3})})})}); m.addLayer(markerLayer);
  let last=null;
  function feedback(msg,type=''){const e=$('feedback');e.textContent=msg;e.className='feedback '+type;}
  function parseNum(str){const t=String(str).trim().replace(',','.');if(!/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$/.test(t))return NaN;return Number(t);}
  function isDummy(s){return /(?:291\s?000\s?000|960\s?000\s?00|exemplo@)/i.test(s||'');}
  function makeNode(tag,text,cls){const e=document.createElement(tag);if(cls)e.className=cls;if(text!=null)e.textContent=String(text);return e;}
  function identify(coordinate){const result=[];refs.forEach(ref=>{if(!ref.layer||!ref.layer.getSource)return;const source=ref.layer.getSource();if(!source||!source.getFeatures)return;const matches=source.getFeaturesInExtent?source.getFeaturesInExtent([coordinate[0],coordinate[1],coordinate[0],coordinate[1]]):source.getFeatures();for(const f of matches){const geom=f.getGeometry();if(!geom||!geom.intersectsCoordinate(coordinate))continue;const rawContact=ref.key==='municipios'?(window.SARGACO_MUNICIPAL_CONTACTS||{})[String(f.get('Municipio')||'')]||null:f.get('Contacto');result.push({type:ref.name,name:f.get(ref.field)||'Área sem designação',contact:rawContact||null,placeholder:isDummy(rawContact)});}});return result;}
  // Regra de encaminhamento indicativo para pontos marítimos próximos das ilhas.
  // Os polígonos municipais identificam terra; os limites abaixo são apenas
  // uma área de pesquisa, NÃO delimitam jurisdição marítima legal.
  function inIslandVicinity(lat,lon){
    return (lon>=-17.60&&lon<=-16.60&&lat>=32.45&&lat<=33.00) ||
           (lon>=-16.65&&lon<=-16.10&&lat>=32.90&&lat<=33.30);
  }
  function maritimeFallback(lat,lon,hits){
    const onLand=hits.some(h=>h.type==='Município');
    const inPort=hits.some(h=>h.type==='Área portuária');
    // A ausência de cobertura nas outras camadas não exclui responsabilidade marítima.
    return !onLand && !inPort && inIslandVicinity(lat,lon);
  }
  function showResult(lat,lon,hits,isMaritime){const el=$('result');el.replaceChildren();el.appendChild(makeNode('div',`${lat.toFixed(6)}, ${lon.toFixed(6)}`,'result-tag'));el.appendChild(makeNode('h3',hits.length?`${hits.length} área(s) sobreposta(s)`:(isMaritime?'Área marítima — Autoridade Marítima':'Sem correspondência nas áreas cartografadas')));
    if(hits.length){const ul=makeNode('ul',null,'result-list');hits.forEach(h=>{const li=makeNode('li');li.appendChild(makeNode('b',h.type+' · '+h.name));if(h.contact){li.appendChild(makeNode('small',h.placeholder?'Contacto no ficheiro original — não validado':h.contact,h.placeholder?'contact-placeholder':''));}ul.appendChild(li);});el.appendChild(ul);}else if(isMaritime){el.appendChild(makeNode('p','Ponto no mar, fora das áreas específicas representadas. Encaminhamento indicativo: Autoridade Marítima.'));el.appendChild(makeNode('p','Esta indicação não constitui delimitação oficial de jurisdição. Confirme a competência territorial e eventuais áreas de jurisdição portuária antes de qualquer atuação.','notice'));}else{el.appendChild(makeNode('p','O ponto não coincide com os polígonos presentes na base. Não é possível determinar automaticamente a entidade competente.'));}
    el.appendChild(makeNode('p','A identificação é indicativa e pode apresentar áreas sobrepostas.','notice'));
  }
  function locate(ev){if(ev)ev.preventDefault();const lat=parseNum($('latitude').value),lon=parseNum($('longitude').value);if(!Number.isFinite(lat)||!Number.isFinite(lon)||lat< -90||lat>90||lon< -180||lon>180){feedback('Introduza coordenadas válidas: latitude entre −90 e 90 e longitude entre −180 e 180.','error');return;}
    const xy=ol.proj.transform([lon,lat],'EPSG:4326',projection);if(!xy||xy.some(v=>!Number.isFinite(v))){feedback('Não foi possível converter as coordenadas.','error');return;}
    const feature=new ol.Feature({geometry:new ol.geom.Point(xy),name:`${lat}, ${lon}`});points.clear();points.addFeature(feature);const hits=identify(xy);const isMaritime=maritimeFallback(lat,lon,hits);const displayHits=isMaritime?[]:hits;showResult(lat,lon,displayHits,isMaritime);last={lat,lon};$('copy-coords').disabled=false;feedback(isMaritime?'Ponto marítimo: encaminhamento indicativo para a Autoridade Marítima.':(hits.length?'Localização encontrada. Consulte as áreas identificadas.':'Ponto localizado, sem correspondência nas áreas cartografadas.'),'success');m.getView().animate({center:xy,zoom:13,duration:450});}
  $('coord-input-form').addEventListener('submit',locate);
  $('refresh-points').addEventListener('click',()=>{points.clear();last=null;$('latitude').value='';$('longitude').value='';$('copy-coords').disabled=true;$('result').replaceChildren(makeNode('div','Nenhum ponto selecionado.','empty'));feedback('Pontos removidos. Introduza novas coordenadas para consultar.');});
  $('copy-coords').addEventListener('click',async()=>{if(!last)return;const str=`${last.lat.toFixed(6)}, ${last.lon.toFixed(6)}`;try{await navigator.clipboard.writeText(str);feedback('Coordenadas copiadas.','success');}catch(e){feedback('Não foi possível copiar automaticamente. Selecione as coordenadas no resultado.','error');}});
  document.querySelectorAll('input[data-layer]').forEach(el=>{el.addEventListener('change',()=>{const ref=refs.find(r=>r.key===el.dataset.layer);if(ref&&ref.layer)ref.layer.setVisible(el.checked);});});
  const home=[333318.60,3634315.09];function center(x,y,z){m.getView().animate({center:ol.proj.transform([x,y],'EPSG:4326',projection),zoom:z,duration:400});}
  $('reset-map').addEventListener('click',()=>m.getView().animate({center:home,zoom:11,duration:400}));
  $('view-madeira').addEventListener('click',()=>center(-16.95,32.74,10));
  $('view-porto-santo').addEventListener('click',()=>center(-16.34,33.07,12));
  m.updateSize();window.addEventListener('resize',()=>m.updateSize());
}
if(document.readyState==='complete')init();else window.addEventListener('load',init);
})();