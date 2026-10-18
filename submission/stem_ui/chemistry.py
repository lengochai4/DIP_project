"""Small educational molecular editor; no reaction/energy/depth simulation."""
from collections import Counter, OrderedDict
from dataclasses import dataclass
from pathlib import Path
import copy
import json
import math
import re
import numpy as np

DATA=Path(__file__).with_name('data')/'pubchem-periodic-table.json'


@dataclass(frozen=True)
class Element:
    number: int
    symbol: str
    name: str
    configuration: str
    shells: tuple[int,...]
    color: tuple[float,float,float]
    block: str


def load_elements():
    source=json.loads(DATA.read_text(encoding='utf-8'))['Table']
    columns=source['Columns']['Column']
    raw={row['Cell'][1]:dict(zip(columns,row['Cell'])) for row in source['Row']}
    def subshells(symbol):
        config=raw[symbol]['ElectronConfiguration']
        bracket=re.search(r'\[([A-Za-z]+)\]',config)
        counts=subshells(bracket[1]) if bracket else {}
        for n,kind,count in re.findall(r'(\d)([spdf])(\d+)',config):
            counts[(int(n),kind)]=int(count)
        return counts
    elements={}
    for symbol,row in raw.items():
        counts=subshells(symbol)
        by_shell=Counter()
        for (n,_),count in counts.items(): by_shell[n]+=count
        number=int(row['AtomicNumber'])
        shells=tuple(by_shell[n] for n in range(1,max(by_shell)+1))
        if sum(shells)!=number: raise ValueError(f'Electron configuration mismatch: {symbol}')
        color=row['CPKHexColor'].zfill(6) if row['CPKHexColor'] else 'A0B0C0'
        rgb=tuple(max(.18,int(color[i:i+2],16)/255) for i in (0,2,4))
        elements[symbol]=Element(number,symbol,row['Name'],row['ElectronConfiguration'],shells,rgb,row['GroupBlock'])
    return elements


@dataclass
class Atom:
    id: int
    symbol: str
    position: np.ndarray
    target: np.ndarray
    scale: float = 1.0


class ChemistryScene:
    def __init__(self, settings):
        self.settings=settings
        self.elements=load_elements()
        self.atoms={}; self.bonds={}; self.next_id=1
        self.selected=None; self.edit=False; self.electrons=False; self.order=1
        self.undo_stack=[]; self.redo_stack=[]
        self.message='Chọn bảng nguyên tố để bắt đầu'
        self.revision=0
        self._transaction=None
        self._description_cache=OrderedDict()
        self._templates=[]
        for key,t in settings['chemistry_templates'].items():
            symbols=tuple(t['symbols']); positions=np.asarray(t['positions'],dtype=float)
            if not symbols or len(symbols)>settings['chemistry_max_atoms'] or any(s not in self.elements for s in symbols):
                raise ValueError(f'Invalid template atoms: {key}')
            if positions.shape!=(len(symbols),3) or not np.all(np.isfinite(positions)) or np.max(np.abs(positions))>settings['chemistry_scene_limit']-1:
                raise ValueError(f'Invalid template positions: {key}')
            graph=[{} for _ in symbols]
            for a,b,n in t['bonds']:
                if any(isinstance(v,bool) or not isinstance(v,int) for v in (a,b,n)) or not (0<=a<len(symbols) and 0<=b<len(symbols)) or a==b or n not in (1,2,3) or b in graph[a]:
                    raise ValueError(f'Invalid template bond: {key}')
                graph[a][b]=n; graph[b][a]=n
            for i,s in enumerate(symbols):
                cap=settings['chemistry_covalent_limits'].get(s)
                if cap is None or sum(graph[i].values())!=cap:
                    raise ValueError(f'Unsupported or incomplete neutral template valence: {key}')
            seen={0}; todo=[0]
            while todo:
                for j in graph[todo.pop()]:
                    if j not in seen: seen.add(j); todo.append(j)
            if len(seen)!=len(symbols): raise ValueError(f'Disconnected template: {key}')
            self._templates.append((t['label'],symbols,graph))

    def state(self):
        return {'schema':1,'kind':'illustrative_molecular_graph','positions_are':'display_scene_units',
            'atoms':[{'id':a.id,'symbol':a.symbol,'position':a.position.tolist(),'display_scale':a.scale} for a in self.atoms.values()],
            'bonds':[{'a':a,'b':b,'order':order} for (a,b),order in self.bonds.items()]}

    def restore(self,state):
        if not isinstance(state,dict): raise ValueError('Không đúng định dạng không gian hóa học')
        if state.get('schema')!=1 or state.get('kind')!='illustrative_molecular_graph':
            raise ValueError('Không đúng định dạng không gian hóa học')
        rows=state['atoms']
        if len(rows)>self.settings['chemistry_max_atoms']: raise ValueError('Quá nhiều nguyên tử')
        atoms={}
        for row in rows:
            i=row['id']; p=np.array(row['position'],dtype=float)
            if isinstance(i,bool) or not isinstance(i,int) or i<1 or i in atoms or row['symbol'] not in self.elements:
                raise ValueError('Danh tính nguyên tử không hợp lệ')
            if p.shape!=(3,) or not np.all(np.isfinite(p)) or np.max(np.abs(p))>self.settings['chemistry_scene_limit']:
                raise ValueError('Vị trí nguyên tử không hợp lệ')
            scale=float(row.get('display_scale',1.))
            if not math.isfinite(scale) or not self.settings['grab_min_scale']<=scale<=self.settings['grab_max_scale']:
                raise ValueError('Cỡ hiển thị nguyên tử không hợp lệ')
            atoms[i]=Atom(i,row['symbol'],p,p.copy(),scale)
        bonds={}; valences=Counter()
        for row in state['bonds']:
            a,b,order=row['a'],row['b'],row['order']
            if any(isinstance(v,bool) or not isinstance(v,int) for v in (a,b,order)) or a not in atoms or b not in atoms or a==b or order not in (1,2,3):
                raise ValueError('Liên kết không hợp lệ')
            key=tuple(sorted((a,b)))
            if key in bonds: raise ValueError('Liên kết trùng')
            bonds[key]=order; valences[a]+=order; valences[b]+=order
        for i,v in valences.items():
            cap=self.settings['chemistry_covalent_limits'].get(atoms[i].symbol)
            if cap is None or v>cap: raise ValueError('Liên kết vượt phạm vi hóa trị demo')
        # Validate completely before replacing an existing workspace.
        self.atoms=atoms; self.bonds=bonds; self.next_id=max(atoms,default=0)+1
        self.selected=None; self.revision+=1

    def remember(self):
        self.undo_stack.append(copy.deepcopy(self.state()))
        self.undo_stack=self.undo_stack[-self.settings['chemistry_history_limit']:]
        self.redo_stack.clear()

    def begin_edit(self):
        if self._transaction is None: self._transaction=copy.deepcopy(self.state())

    def finish_edit(self):
        if self._transaction is not None and self._transaction!=self.state():
            self.undo_stack.append(self._transaction)
            self.undo_stack=self.undo_stack[-self.settings['chemistry_history_limit']:]
            self.redo_stack.clear()
        self._transaction=None

    def undo(self,redo=False):
        self.finish_edit()
        stack=self.redo_stack if redo else self.undo_stack
        other=self.undo_stack if redo else self.redo_stack
        if not stack: return
        other.append(self.state()); self.restore(stack.pop())
        self.message='Đã làm lại' if redo else 'Đã hoàn tác'

    def add(self,symbol,position):
        if symbol not in self.elements: raise ValueError('Unknown element')
        if len(self.atoms)>=self.settings['chemistry_max_atoms']:
            self.message='Đã đủ nguyên tử trong không gian; xóa bớt để thêm'; return None
        p=np.asarray(position,dtype=float)
        if p.shape!=(3,) or not np.all(np.isfinite(p)): raise ValueError('Invalid atom position')
        self.remember(); i=self.next_id; self.next_id+=1
        p=np.clip(p,-self.settings['chemistry_scene_limit'],self.settings['chemistry_scene_limit'])
        self.atoms[i]=Atom(i,symbol,p,p.copy()); self.selected=i; self.revision+=1
        self.message=f'Đã tạo {symbol}; chụm trên nguyên tử để kéo'
        return i

    def component(self,start):
        found={start}; queue=[start]
        while queue:
            i=queue.pop()
            for a,b in self.bonds:
                other=b if a==i else a if b==i else None
                if other is not None and other not in found: found.add(other); queue.append(other)
        return tuple(sorted(found))

    def valence(self,i):
        return sum(order for pair,order in self.bonds.items() if i in pair)

    def can_bond(self,a,b,order=None):
        order=self.order if order is None else order
        if a==b or a not in self.atoms or b not in self.atoms or order not in (1,2,3): return False
        old=self.bonds.get(tuple(sorted((a,b))),0)
        for i in (a,b):
            limit=self.settings['chemistry_covalent_limits'].get(self.atoms[i].symbol)
            if limit is None or self.valence(i)-old+order>limit: return False
        return True

    def bond(self,a,b,order=None,history=True):
        order=self.order if order is None else order
        if not self.can_bond(a,b,order):
            self.message='Không hỗ trợ liên kết này trong mô hình cộng hóa trị trung hòa'; return False
        key=tuple(sorted((a,b)))
        if self.bonds.get(key)==order: return False
        if history: self.remember()
        self.bonds[key]=order; self.revision+=1
        self.message='Đã ghép → '+self.describe(self.component(a))
        return True

    def move_atom(self,i,target):
        p=np.asarray(target,dtype=float)
        if p.shape!=(3,) or not np.all(np.isfinite(p)): return
        self.atoms[i].target=np.clip(p,-self.settings['chemistry_scene_limit'],self.settings['chemistry_scene_limit'])
        # Removing a link is an editor action, not a prediction of bond energy.
        for pair in list(self.bonds):
            if i in pair:
                other=pair[1] if pair[0]==i else pair[0]
                scale=(self.atoms[i].scale+self.atoms[other].scale)/2
                if np.linalg.norm(self.atoms[i].target-self.atoms[other].position)>self.settings['chemistry_break_distance']*scale:
                    del self.bonds[pair]; self.revision+=1
                    parts=[]
                    for start in (i,other):
                        ids=self.component(start)
                        if ids not in parts: parts.append(ids)
                    self.message='Đã tách → '+' + '.join(self.describe(ids) for ids in parts)

    def link_nearby(self,i,exclude=()):
        candidates=sorted((float(np.linalg.norm(a.position-self.atoms[i].position)),j)
            for j,a in self.atoms.items() if j!=i and j not in exclude)
        for distance,j in candidates:
            if self.bonds.get(tuple(sorted((i,j))))==self.order: continue
            scale=(self.atoms[i].scale+self.atoms[j].scale)/2
            if distance<=self.settings['chemistry_join_distance']*scale and self.can_bond(i,j):
                return self.bond(i,j,history=False)
        self.message='Đã đặt nguyên tử; chưa ghép liên kết mới'
        return False

    def delete_selected(self):
        if self.selected not in self.atoms: return
        self.remember()
        ids=(self.selected,) if self.edit else self.component(self.selected)
        for i in ids: del self.atoms[i]
        self.bonds={pair:n for pair,n in self.bonds.items() if not any(i in ids for i in pair)}
        self.selected=None; self.revision+=1; self.message='Đã xóa đối tượng đang chọn'

    def advance(self,dt):
        if not math.isfinite(dt) or dt<=0: return
        for atom in self.atoms.values():
            error=float(np.linalg.norm(atom.target-atom.position))
            hz=min(self.settings['display_response_max_hz'],self.settings['chemistry_response_hz']+error*self.settings['pose_response_gain'])
            atom.position+=(1-math.exp(-math.tau*hz*dt))*(atom.target-atom.position)

    def freeze(self,ids):
        for i in ids:
            if i in self.atoms: self.atoms[i].target=self.atoms[i].position.copy()

    def formula(self,ids):
        counts=Counter(self.atoms[i].symbol for i in ids)
        order=(['C']+(['H'] if 'H' in counts else [])+sorted(set(counts)-{'C','H'})) if 'C' in counts else sorted(counts)
        return ''.join(s+(str(counts[s]) if counts[s]>1 else '') for s in order)

    def describe(self,ids):
        actual=tuple(sorted(ids)); indices={i:n for n,i in enumerate(actual)}
        symbols=tuple(self.atoms[i].symbol for i in actual)
        links=tuple(sorted((indices[a],indices[b],n) for (a,b),n in self.bonds.items() if a in indices and b in indices))
        key=(symbols,links)
        if key in self._description_cache:
            self._description_cache.move_to_end(key)
            return self._description_cache[key]
        graph=[{} for _ in symbols]
        for a,b,n in links: graph[a][b]=n; graph[b][a]=n
        label=self.formula(actual)+' • mô hình đang xây dựng'
        for candidate,template_symbols,template_graph in self._templates:
            if Counter(symbols)==Counter(template_symbols) and graph_matches(symbols,graph,template_symbols,template_graph):
                label=candidate; break
        self._description_cache[key]=label
        if len(self._description_cache)>128: self._description_cache.popitem(last=False)
        return label

    def add_template(self,key):
        t=self.settings['chemistry_templates'][key]
        if len(self.atoms)+len(t['symbols'])>self.settings['chemistry_max_atoms']:
            self.message='Không đủ chỗ để thêm mẫu'; return
        self.remember(); ids=[]
        origin=np.array((.9,0.,0.))
        for s,p in zip(t['symbols'],t['positions']):
            i=self.next_id; self.next_id+=1; v=origin+np.array(p,dtype=float)
            self.atoms[i]=Atom(i,s,v,v.copy()); ids.append(i)
        for a,b,n in t['bonds']: self.bonds[tuple(sorted((ids[a],ids[b])))]=n
        self.selected=ids[0]; self.revision+=1; self.message='Đã thêm '+t['label']+'; hình học minh họa'

    def save(self,path):
        path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
        temporary=path.with_suffix('.tmp')
        temporary.write_text(json.dumps(self.state(),ensure_ascii=False,indent=2),encoding='utf-8')
        temporary.replace(path); self.message='Đã lưu không gian'; self.revision+=1

    def load(self,path):
        state=json.loads(Path(path).read_text(encoding='utf-8'))
        before=self.state(); self.restore(state)
        self.undo_stack.append(before); self.redo_stack.clear(); self.message='Đã mở không gian đã lưu'


def graph_matches(symbols,graph,template_symbols,template_graph):
    """Exact colored/bond-order graph match, pruning before assignment.

    Coordinates do not identify molecules. Degree/neighbor signatures avoid
    factorial enumeration of interchangeable hydrogen atoms in larger presets.
    This identifies connectivity only, not stereochemistry or stability.
    """
    if len(symbols)!=len(template_symbols): return False
    def signatures(labels,adj):
        return [(s,len(adj[i]),sum(adj[i].values()),tuple(sorted(Counter((labels[j],n) for j,n in adj[i].items()).items()))) for i,s in enumerate(labels)]
    actual=signatures(symbols,graph); expected=signatures(template_symbols,template_graph)
    if Counter(actual)!=Counter(expected): return False
    candidates={i:tuple(j for j,signature in enumerate(actual) if signature==sig) for i,sig in enumerate(expected)}
    order=sorted(candidates,key=lambda i:(len(candidates[i]),-len(template_graph[i])))
    mapped={}; used=set()
    def assign(offset):
        if offset==len(order): return True
        i=order[offset]
        for j in candidates[i]:
            if j in used or any(template_graph[i].get(k,0)!=graph[j].get(v,0) for k,v in mapped.items()): continue
            mapped[i]=j; used.add(j)
            if assign(offset+1): return True
            used.remove(j); del mapped[i]
        return False
    return assign(0)
