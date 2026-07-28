
class FaceFanData:
    """Calcola le grandezze geometriche del ventaglio innalzato su una faccia.

    A partire dai tre vertici della faccia e dal parametro adimensionale `param`
    (che regola quanto viene sollevato l'apice sopra il baricentro), ricava:
      - base_edge     : lunghezza dello spigolo di base della faccia,
      - triangle_side : lato inclinato dall'apice sollevato a un vertice di base,
      - h             : distanza dall'apice al punto medio dello spigolo di base,
      - radius        : raggio dell'arco di raccordo (vedi _compute_radius),
      - h1_low, h1    : quote geometriche del centro dell'arco,
      - theta         : angolo di apertura del ventaglio.
    Espone inoltre i punti/direzioni di base della faccia (center, normal, p3,
    p01), riutilizzati da FaceFan per generare i punti 3D senza ricalcolarli.
    """

    def __init__(self, pts, param):
        p0,p1,p2 = pts
        self.param = param
        # Spigolo di base della faccia (i triangoli sono equilateri: basta un lato).
        self.base_edge = base_edge = p0.dist(p1)
        self.center = center = (p0+p1+p2)/3        # baricentro della faccia
        self.normal = normal = (p1-p0).cross(p2-p0).normalized()  # normale uscente alla faccia
        # Apice sollevato sopra il baricentro lungo la normale, di param*base_edge.
        self.p3 = p3 = center + normal * (param * base_edge)
        # Lato inclinato: distanza da un vertice di base all'apice sollevato.
        self.triangle_side = triangle_side = p0.dist(p3)
        self.p01 = p01 = (pts[0]+pts[1])/2      # punto medio dello spigolo di base p0-p1
        # Altezza del triangolo laterale: dall'apice al punto medio dello spigolo.
        self.h = h = (p3-p01).length()

        # Raggio dell'arco di circonferenza che raccorda le facce adiacenti.
        self.radius = radius = self._compute_radius(triangle_side, base_edge)

        # Quote del centro dell'arco rispetto allo spigolo di base:
        # h1_low = distanza dal centro dell'arco alla corda (spigolo di base).
        self.h1_low = h1_low = (radius**2-(base_edge/2)**2)**0.5
        self.h1 = h1 = radius + h1_low

        # Angolo di apertura theta del ventaglio, ottenuto scomponendo l'angolo
        # nel triangolo che lega apice, punto medio dello spigolo e centro dell'arco.
        theta0 = np.arcsin((param*base_edge)/h)
        theta1 = compute_angle_from_sides(triangle_side, h, h1)
        theta = np.pi - (theta0 + theta1)
        self.theta = theta

    def _compute_radius(self, a, b):
        """Trova per bisezione il raggio r dell'arco tale che f(r, a) = b.

        f(r, a) = 2 r sin(pi - 4 arcsin(a/(2r))) è la corda sottesa dall'arco in
        funzione del raggio; la si inverte numericamente affinché combaci con la
        lunghezza `b` (lo spigolo di base). Gli estremi r0, r1 racchiudono la
        soluzione e le assert verificano che il segno sia opposto (radice interna).
        """
        def f(r,a):
            phi = (np.pi - 4*np.arcsin(a*0.5/r))
            return 2 * r * np.sin(phi)
        r0 = a/2**0.5
        r1 = a/(2*np.sin(np.pi/8))
        assert f(r0,a)<b
        assert f(r1,a)>b
        assert r0<r1
        while r1-r0>1.0e-15:
            r = (r0+r1)/2
            v = f(r,a)
            if v<b: r0=r
            else: r1=r
        return r

def get_M2_parameter():
    """Determina per bisezione il parametro `param` caratteristico del modello M2.

    Si cerca il valore per cui l'angolo di apertura del ventaglio (theta) è pari a
    metà dell'angolo diedro dell'icosaedro, arccos(-sqrt(5)/3): questa condizione
    fa sì che i ventagli di due facce adiacenti si raccordino correttamente lungo
    lo spigolo comune.
    """
    face = Polyhedron.ico.get_face_vertices(0)
    def f(param):
        p = FaceFanData(face, param)
        return p.theta
    dihedral_angle = np.arccos(-5**0.5/3)

    target = dihedral_angle/2 #(2*np.pi - dihedral_angle)/2

    # Intervallo iniziale: theta è decrescente in param, quindi f(p0)>target>f(p1).
    p0 = 0.2
    p1 = 1.0
    assert f(p0)>target
    assert f(p1)<target

    while p1-p0>1.0e-15:
        p = (p0+p1)/2
        v = f(p)
        if v>target: p0 = p
        else: p1 = p
    return p

class FaceFan:
    """Genera i punti 3D del ventaglio costruito su una singola faccia triangolare.

    A partire dai tre vertici della faccia (pts) e dal parametro adimensionale
    `parameter` — dal quale ricava internamente i FaceFanData — colloca nello spazio:
      - p0, p1, p2 : i vertici originali della faccia,
      - p3         : l'apice sollevato sopra il baricentro,
      - q0         : il vertice dell'arco sul piano di simmetria del ventaglio,
      - q1, q2     : gli estremi laterali dell'arco di raccordo.
    Il risultato è salvato in self.points come lista di tuple (x, y, z).
    """

    def __init__(self, pts, parameter):
        self.pts = pts
        p0,p1,p2 = pts
        face_fan_data = FaceFanData(pts, parameter)

        # Punti e direzioni della faccia, già calcolati da FaceFanData.
        center = face_fan_data.center   # baricentro della faccia
        normal = face_fan_data.normal   # normale uscente
        p3 = face_fan_data.p3           # apice sollevato sopra il baricentro
        p01 = face_fan_data.p01         # punto medio dello spigolo di base

        # Parametri geometrici precalcolati.
        theta = face_fan_data.theta
        radius = face_fan_data.radius
        h1 = face_fan_data.h1
        h1_low = face_fan_data.h1_low
        triangle_side = face_fan_data.triangle_side

        # Terna ortonormale locale del ventaglio:
        #  e0 = direzione dal centro verso il punto medio dello spigolo (nel piano faccia),
        #  e1 = e0 ruotato di theta verso la normale (direzione di apertura del ventaglio),
        #  e2 = direzione dello spigolo di base (per l'apertura laterale dell'arco).
        e0 = (p01-center).normalized()
        e1 = e0 * np.cos(theta) + normal * np.sin(theta)
        e2 = (p1-p0).normalized()

        # q0: punto dell'arco sul piano di simmetria, a distanza h1 lungo e1.
        q0 = p01 + e1 * h1
        # phi: semiapertura angolare dell'arco vista dal suo centro.
        phi = 2 * np.arcsin(triangle_side/(2*radius))
        # q1, q2: estremi laterali dell'arco, ottenuti ruotando di ±phi attorno al centro.
        q1 = p01 + e1 * h1_low + (e1 * np.cos(phi) + e2 * np.sin(phi)) * radius
        q2 = p01 + e1 * h1_low + (e1 * np.cos(phi) - e2 * np.sin(phi)) * radius

        # Esporta tutti i punti come tuple (x, y, z).
        self.points = [p.tup() for p in [p0,p1,p2,p3,q0,q1,q2]]


#def get_M2_face_fan():
#    """Comodità: restituisce i FaceFanData della faccia 0 dell'icosaedro
#    valutati con il parametro caratteristico del modello M2."""
#    return FaceFan(Polyhedron.ico.get_face_vertices(0), get_M2_parameter())


def make_M2_mesh_data():
    """Assembla l'intera mesh del modello M2 percorrendo le 20 facce dell'icosaedro.

    Il parametro caratteristico viene calcolato una sola volta. Per ogni faccia si
    generano tre ventagli, uno per ciascuna rotazione ciclica dei suoi vertici (così
    ogni spigolo/angolo riceve la sua porzione di raccordo). Ogni FaceFan produce 7
    punti (p0,p1,p2,p3,q0,q1,q2, indici locali 0..6) da cui si ricavano 4 triangoli
    a raggiera attorno all'apice p3. Gli indici sono traslati di `k`, cioè il numero
    di vertici già accumulati, per riferirsi alla lista globale.
    """
    ico = Polyhedron.ico
    param = get_M2_parameter()

    mesh_data = MeshData()

    for face_index in range(len(ico.faces)):
        face = ico.get_face_vertices(face_index)
        # Tre orientamenti della faccia: ruota ciclicamente i vertici (p0,p1,p2).
        for vindex in range(3):
            pts = [face[(vindex+i)%3] for i in range(3)]
            fan = FaceFan(pts, param)
            k = len(mesh_data.vertices)  # offset di questo ventaglio nella lista globale
            mesh_data.vertices.extend(fan.points)
            # Quattro triangoli a ventaglio attorno all'apice p3 (indice locale 3):
            # collegano l'apice a p1, q1, q0, q2, p0 in sequenza.
            mesh_data.faces.extend([
                [k+3,k+1,k+5],
                [k+3,k+5,k+4],
                [k+3,k+4,k+6],
                [k+3,k+6,k+0]
            ])
    return mesh_data

def make_M2_fan_mesh_data(face_index, param):

    ico = Polyhedron.ico
    mesh_data = MeshData()

    face = ico.get_face_vertices(face_index)
    # Tre orientamenti della faccia: ruota ciclicamente i vertici (p0,p1,p2).
    for vindex in range(3):
        pts = [face[(vindex+i)%3] for i in range(3)]
        fan = FaceFan(pts, param)
        k = len(mesh_data.vertices)  # offset di questo ventaglio nella lista globale
        mesh_data.vertices.extend(fan.points)
        # Quattro triangoli a ventaglio attorno all'apice p3 (indice locale 3):
        # collegano l'apice a p1, q1, q0, q2, p0 in sequenza.
        mesh_data.faces.extend([
            [k+3,k+1,k+5],
            [k+3,k+5,k+4],
            [k+3,k+4,k+6],
            [k+3,k+6,k+0]
        ])
    return mesh_data

