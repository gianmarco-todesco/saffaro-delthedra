import math
from geometry import Vector, MeshData

def make_M2_fan(phi):
    sn_half_phi = math.sin(phi/2)
    r = 0.5/sn_half_phi
    assert r<1
    a = math.sin(2*phi)/sn_half_phi
    cm = (1-r**2)**0.5 # distanza dal centro del cerchio al centro della fan 
    cp = (1-(a/2)**2)**0.5 # distanza dal centro della fan al punto medio del lato del triangolo di base
    cq = (cp**2-a**2/12)**0.5 # altezza del centro della fan rispetto al triangolo di base
    cpq = math.asin(cq/cp) 
    cpm = math.asin(cm/cp)
    offset = r*math.cos(math.pi-2*phi)
    theta = math.pi - cpq - cpm # angolo fra il piano che contiene i punti p0..p4 e il piano orizzontale
    cs_theta = math.cos(theta)
    sn_theta = math.sin(theta)
    
    base_r = a * 3**0.5/3
    base = []
    for i in range(3):
        angle = math.pi*2*(i+1)/3
        base.append(Vector((base_r*math.cos(angle), base_r*math.sin(angle), 0)))
    pts = []
    for i in range(3):
        pa = base[i]
        pb = base[(i+1)%3]
        pab = (pa+pb)/2
        e0 = (pb-pa).normalized()
        e1 = pab.normalized() * cs_theta + Vector((0,0,1))*sn_theta        
        orig = pab + e1 * offset
        pts.append(pa.tup())        
        for j in range(-1,2):
            angle = j*phi
            x = r * math.sin(angle)
            y = r * math.cos(angle)
            p = orig + e0 * x + e1 * y
            pts.append(p.tup())
    pts.append((0,0,cq))
    faces = []
    for i in range(12):
        faces.append([12,i,(i+1)%12])

    mesh_data = MeshData()
    mesh_data.vertices = pts
    mesh_data.faces = faces
    return mesh_data


# print()
