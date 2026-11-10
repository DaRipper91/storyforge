"""Unverified remaining batch-A elf construction draft; excluded from delivered assets."""
from humanoid_a_common import *

def elf_hero(src, out, slug, cfg):
    """Build layered humanoid clothing, braided hair and articulated hands from a race palette.

    These shared construction primitives retain independent materials and silhouettes per race;
    ornaments, mantle shapes, armour and carried equipment follow each concept sheet.
    """
    bpy.ops.wm.read_factory_settings(use_empty=True)
    rng = random.Random(cfg['seed'])
    skin = mat(slug+'_skin', cfg['skin'], .68)
    cloth = mat(slug+'_linen', cfg['cloth'], .88)
    overlay = mat(slug+'_overlay', cfg['overlay'], .75)
    leather = mat(slug+'_leather', cfg['leather'], .66)
    trim = mat(slug+'_trim', cfg['trim'], .36, .65)
    hair = mat(slug+'_hair', cfg['hair'], .56)
    lip = mat(slug+'_lips', tuple(c*.65 for c in cfg['skin']), .65)
    dark = mat(slug+'_dark', (.012,.009,.016), .65)
    white = mat(slug+'_sclera', (.58,.55,.55), .4)
    eye = mat(slug+'_iris', cfg['eye'], .3)
    arm = prep(src, skin, leather)
    tex = os.path.join(out,'tex')
    T.bind(cloth,*tex_surface(tex,slug+'_linen',cfg['cloth'],cfg['seed'],'cloth',n=1024,wear=.4,normal_strength=.7))
    T.bind(overlay,*tex_surface(tex,slug+'_overlay',cfg['overlay'],cfg['seed']+1,'cloth',n=512,wear=.35,accent=cfg['trim'],normal_strength=.65))
    T.bind(leather,*tex_surface(tex,slug+'_leather',cfg['leather'],cfg['seed']+2,'leather',n=512,wear=.4,normal_strength=.7))
    T.bind(skin,*tex_surface(tex,slug+'_skin',cfg['skin'],cfg['seed']+3,'skin',n=512,wear=.1,normal_strength=.25))
    uv_arm_cyl(next(o for o in bpy.data.objects if o.name.endswith('_Body')))
    build_face(arm,skin,lip,hair,eye,white,dark,dict(ear='point',ear_len=cfg.get('ear_len',.07),jaw=.9,chin=.85,brow=.7,nose=.9,cheek=.9,face_w=.92,neck=.037))
    face = bpy.data.objects['Hero_Face']; bpy.context.view_layer.objects.active=face
    rm=face.modifiers.new('SculptUnion','REMESH'); rm.mode='VOXEL'; rm.voxel_size=.0025
    bpy.ops.object.modifier_apply(modifier=rm.name)
    sm=face.modifiers.new('SculptRelax','SMOOTH'); sm.factor=.5; sm.iterations=3
    bpy.ops.object.modifier_apply(modifier=sm.name)
    dm=face.modifiers.new('FaceBudget','DECIMATE'); dm.ratio=min(1,1800/max(1,len(face.data.polygons)*2))
    bpy.ops.object.modifier_apply(modifier=dm.name)
    for polygon in face.data.polygons: polygon.use_smooth=True
    hands(arm,skin,nail_mat=lip)
    # Fine scalp shell and individual flowing locks. Front roots leave the face exposed.
    bm=bmesh.new()
    def scalp(r,c):
        a=2*math.pi*c; elev=lerp(.08,math.pi/2,r)
        front=max(0,math.cos(a))
        elev=lerp(.12+.62*front,math.pi/2,r)
        return Vector((.083*math.sin(a)*math.cos(elev),-.035-.109*math.cos(a)*math.cos(elev),1.653+.107*math.sin(elev)))
    cap=ring_strip(8,24,scalp); attach(arm,'Hero_HairCap',cap,hair,'Head')
    for i in range(30):
        a=2*math.pi*(i+.5)/30
        if math.cos(a)>.82: continue
        x=.087*math.sin(a); y=-.032-.095*math.cos(a)
        ln=cfg.get('hair_length',.37)*(0.85+.15*rng.random())
        pts=[]
        for k in range(9):
            t=k/8; pts.append(Vector((x+.012*math.sin(t*10+i)*t,y+.07*t+.009*math.cos(t*9+i),1.708-ln*t)))
        sweep(bm,pts,[.012*(1-.85*k/8) for k in range(9)],sides=5,squash=.52)
    attach(arm,'Hero_FlowingHair',bm,hair,'Head')
    bm=bmesh.new()
    # Braids cross the temples into a tied rear plait.
    for sx in (-1,1):
        for strand in range(3):
            pts=[]
            for k in range(16):
                t=k/15; a=lerp(.55,2.8,t)*sx
                pts.append(Vector((.086*math.sin(a)+.004*math.sin(t*42+strand*2.094),-.033-.10*math.cos(a),1.696-.07*t+.004*math.cos(t*42+strand*2.094))))
            sweep(bm,pts,.004,sides=4)
    attach(arm,'Hero_TempleBraids',bm,hair,'Head')
    # Fitted long tunic. Raised seams and narrow collar make the neck join deliberate.
    def tunic(r,c):
        z=lerp(.94,1.50,r); a=2*math.pi*c
        p=torso_pt(min(z,1.47),a,grow=.008+.003*math.sin(a*9+r*15))
        if z>1.43:
            t=smoothstep(1.43,1.50,z); p.x=lerp(p.x,.045*math.sin(a),t); p.y=lerp(p.y,-.042-.046*math.cos(a),t)
        return p
    skinned(arm,'Hero_Tunic',ring_strip(14,32,tunic),cloth,nearest_w(TORSO_BONES,.035))
    for side,suf in ((1,'L'),(-1,'R')):
        skinned(arm,'Hero_Sleeve_'+suf,sleeve(side,.13,.565,.009,.005,rings=14,sides=14,fold=.0035,seed=cfg['seed']),cloth,arm_w_full(side))
        skinned(arm,'Hero_Bracer_'+suf,sleeve(side,.435,.568,.011,.008,rings=7,sides=12,fold=.002,seed=cfg['seed']),leather,arm_w_full(side))
        skinned(arm,'Hero_Cuff_'+suf,sleeve(side,.555,.57,.012,.009,rings=2,sides=12),trim,arm_w_full(side))
        # Tailored trousers with knee and ankle creases, hidden under split skirts.
        def trouser(r,c,side=side):
            z=lerp(.99,.27,r); a=2*math.pi*c; rr=lerp(.092,.050,r)+.004*math.sin(r*36+a*3)
            return Vector((side*.121+rr*math.cos(a),-.07+rr*.94*math.sin(a),z))
        skinned(arm,'Hero_Trousers_'+suf,ring_strip(17,14,trouser),cloth,nearest_w(side_leg(suf),.035))
        def boot(r,c,side=side):
            z=lerp(.45,.045,r); a=2*math.pi*c; rr=lerp(.065,.052,r)+.002*math.sin(r*34+a*2)
            return Vector((side*.121+rr*math.cos(a),-.065+rr*math.sin(a),z))
        skinned(arm,'Hero_BootShaft_'+suf,ring_strip(16,14,boot),leather,nearest_w(side_leg(suf),.025))
        bm=bmesh.new(); ell(bm,(side*.121,-.125,.050),(.055,.115,.043),seg=12,rings=7)
        attach(arm,'Hero_BootFoot_'+suf,bm,leather,'Foot.'+suf)
        bm=bmesh.new(); ell(bm,(side*.121,-.125,.014),(.058,.122,.014),seg=12,rings=4)
        attach(arm,'Hero_BootSole_'+suf,bm,dark,'Foot.'+suf)
        bm=bmesh.new()
        for zz in (.37,.23):
            for x in (-.014,.014): tube(bm,(side*.121+x,-.134,zz-.012),(side*.121+x,-.134,zz+.012),.002,.002,seg=4)
            for z in (-.012,.012): tube(bm,(side*.121-.014,-.134,zz+z),(side*.121+.014,-.134,zz+z),.002,.002,seg=4)
        attach(arm,'Hero_BootBuckles_'+suf,bm,trim,'LowerLeg.'+suf)
    # Individually layered skirt gores: unequal hems, overlapping folds, weighted to both legs.
    for j in range(8):
        a0=2*math.pi*j/8; width=.91
        bottom=cfg['skirt'] + .075*math.sin(j*2.3)
        def panel(r,c,a0=a0,j=j,bottom=bottom):
            a=a0+(c-.5)*width; z=lerp(1.015,bottom+.085*abs(2*c-1),r)
            rad=lerp(.175,.24,r)+.009*math.sin(c*math.pi*5+j)*(r*.7+.3)
            return Vector((rad*math.sin(a),-.05-rad*.72*math.cos(a),z))
        mesh=strip(13,10,panel)
        skinned(arm,f'Hero_SkirtGore{j}',mesh,overlay if j%2 else cloth,nearest_w(SPINE+['UpperLeg.L','UpperLeg.R','LowerLeg.L','LowerLeg.R'],.065))
        bm=bmesh.new()
        for cc in (0,1): sweep(bm,[panel(k/12,cc) for k in range(13)],.0022,sides=4)
        sweep(bm,[panel(1,k/9) for k in range(10)],.0022,sides=4)
        skinned(arm,f'Hero_SkirtHem{j}',bm,trim,nearest_w(SPINE+['UpperLeg.L','UpperLeg.R','LowerLeg.L','LowerLeg.R'],.065))
    # Structured waist straps and diagonal torso harness.
    for j,zz in enumerate((1.035,.975)):
        def belt(r,c,zz=zz): return torso_pt(zz+(r-.5)*.032,2*math.pi*c,grow=.033,pw=2.3)
        skinned(arm,f'Hero_Belt{j}',ring_strip(2,32,belt),leather,nearest_w(['Hips','Abdomen'],.03))
    for side in (-1,1):
        def strap(r,c,side=side):
            z=lerp(1.47,1.065,r); x=side*lerp(.105,-.11,r)+(c-.5)*.024
            cy,rx,ry=torso_profile(min(z,1.47)); yy=cy-ry*math.sqrt(max(.05,1-(x/(rx+.025))**2))-.020
            return Vector((x,yy,z))
        skinned(arm,'Hero_Harness'+str(side),strip(18,3,strap),leather,nearest_w(TORSO_BONES,.04))
    # Long mantles sweep around the shoulders in overlapping scalloped panels.
    if cfg.get('mantle'):
        for j in range(5):
            a0=lerp(.6,5.7,j/4)
            def cloak(r,c,a0=a0,j=j):
                a=a0+(c-.5)*1.2; z=lerp(1.49,cfg['mantle']+.10*math.cos(c*math.pi*2+j),r)
                rad=lerp(.18,.29,r)+.012*math.sin(c*math.pi*6+r*4+j)*r
                return Vector((rad*math.sin(a),-.026-rad*.76*math.cos(a),z))
            skinned(arm,f'Hero_MantleLayer{j}',strip(17,12,cloak),overlay,nearest_w(TORSO_BONES+['UpperLeg.L','UpperLeg.R','LowerLeg.L','LowerLeg.R'],.065))
            bm=bmesh.new()
            for cc in (0,1): sweep(bm,[cloak(k/16,cc) for k in range(17)],.0025,sides=4)
            sweep(bm,[cloak(1,k/11) for k in range(12)],.0025,sides=4)
            skinned(arm,f'Hero_MantleHem{j}',bm,trim,nearest_w(TORSO_BONES+['UpperLeg.L','UpperLeg.R','LowerLeg.L','LowerLeg.R'],.065))
    # Brooch, temple filigree and a woven collar border.
    bm=bmesh.new()
    for sx in (-1,1):
        pts=[Vector((sx*(.080+.016*math.sin(k/8*math.pi)),-.015+.09*k/8,1.694+.022*math.sin(k/8*math.pi))) for k in range(9)]
        sweep(bm,pts,.0025,sides=4)
    attach(arm,'Hero_TempleJewellery',bm,trim,'Head')
    bm=bmesh.new(); ell(bm,(.105,-.155,1.465),(.018,.007,.018),seg=10,rings=5)
    attach(arm,'Hero_MantleBrooch',bm,trim,'Chest')
    if cfg.get('bark'):
        bark=mat(slug+'_bark',(.18,.12,.065),.9)
        T.bind(bark,*tex_surface(tex,slug+'_bark',(.18,.12,.065),cfg['seed']+4,'bark',n=512,normal_strength=.8))
        bm=bmesh.new(); moss=bmesh.new()
        for sx,suf in ((1,'L'),(-1,'R')):
            for row in range(3):
                for col in range(4):
                    x=sx*(.115+row*.043); y=-.085+col*.041; z=1.49-row*.027
                    pts=[(x-.035,y-.025,z),(x+.035,y-.025,z),(x+.041,y+.018,z-.025),(x,y+.035,z-.05),(x-.041,y+.018,z-.025)]
                    vs=[bm.verts.new(p) for p in pts]; bm.faces.new(vs)
                    if (row+col)%2==0: ell(moss,(x,y-.022,z+.002),(.016,.008,.004),seg=6,rings=3)
        skinned(arm,'Hero_BarkPauldrons',bm,bark,nearest_w(TORSO_BONES+['UpperArm.L','UpperArm.R'],.03))
        green=mat(slug+'_moss',(.18,.22,.055),.95)
        skinned(arm,'Hero_PauldronMoss',moss,green,nearest_w(TORSO_BONES+['UpperArm.L','UpperArm.R'],.03))
        bm=bmesh.new()
        for sx in (-1,1):
            for j in range(8):
                t=j/7; x=sx*(.075+.008*math.sin(j)); z=1.71-.025*t
                vs=[bm.verts.new((x,-.055+.014*j,z)),bm.verts.new((x+sx*.027,-.045+.014*j,z+.012)),bm.verts.new((x+sx*.012,-.025+.014*j,z-.003))]; bm.faces.new(vs)
        attach(arm,'Hero_HairLeaves',bm,green,'Head')
    if cfg.get('crown'):
        bm=bmesh.new()
        for j in range(9):
            a=lerp(-1.8,1.8,j/8); c=Vector((.09*math.sin(a),-.035-.101*math.cos(a),1.725))
            h=.035+.020*(1-abs(j-4)/4)
            pts=[c+Vector((-.012,0,0)),c+Vector((0,0,h)),c+Vector((.012,0,0))]
            sweep(bm,pts,.0025,sides=4)
        attach(arm,'Hero_Crown',bm,trim,'Head')
    # Deterministic simplification of dense curved parts; skinned attributes survive modifiers.
    total=tri_count()
    if total>21600:
        for o in list(bpy.data.objects):
            if o.type=='MESH' and o.name.startswith('Hero_') and len(o.data.polygons)>140:
                bpy.context.view_layer.objects.active=o
                m=o.modifiers.new('DetailBudget','DECIMATE'); m.ratio=max(.5,21000/total-.06)
                bpy.ops.object.modifier_apply(modifier=m.name)
    finish(out,slug)
