"""Read a DWG through AutoCAD itself (accoreconsole + AutoLISP): the drawing as AutoCAD sees it, no converter.

read(dwg) -> dict with
  lines      : [[x1,y1,z1,x2,y2,z2,layer], ...]            LINE
  polylines  : [{"pts":[[x,y,z],...],"closed":0/1,"layer"}] LWPOLYLINE (vertices in WCS)
  leaders    : [{"handle","text","tip":[x,y,z],"landing":[x,y,z],"dogleg":L,"dir":[dx,dy,dz],"th":h,"layer"}]  MULTILEADER
  dims       : [{"value":v,"text":"<>","def1":[..],"def2":[..],"textpos":[..]}]                             DIMENSION
  layouts    : [{"name","paper":[w,h],"units":n,"viewports":[[x0,y0,x1,y1],...],"frames":[[x0,y0,x1,y1],...]}]
Usage: python tools/acad_read.py <dwg> [--out json]
"""
import json, os, sys, tempfile, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import acad_core as C

LISP = r'''
(defun j-num (v) (if (numberp v) (rtos v 2 4) "0"))
(defun j-pt (p) (strcat "[" (j-num (car p)) "," (j-num (cadr p)) "," (j-num (if (caddr p) (caddr p) 0.0)) "]"))
(defun j-str (s / out i c) (setq out "" i 1)
  (while (<= i (strlen s)) (setq c (substr s i 1))
    (cond ((= c "\"") (setq out (strcat out "\\\""))) ((= c "\\") (setq out (strcat out "\\\\"))) ((< (ascii c) 32) (setq out (strcat out " "))) (t (setq out (strcat out c))))
    (setq i (1+ i))) out)
(defun wcs (p ext) (trans p ext 0))
(defun dump-line (e d) (strcat "[" (j-pt (cdr (assoc 10 d))) "," (j-pt (cdr (assoc 11 d))) ",\"" (j-str (cdr (assoc 8 d))) "\"]"))
(defun dump-pline (e d / ext elev pts out)
  (setq ext (cdr (assoc 210 d)) elev (cdr (assoc 38 d)) out "")
  (if (null elev) (setq elev 0.0))
  (foreach a d (if (= (car a) 10) (setq out (strcat out (if (= out "") "" ",") (j-pt (wcs (list (car (cdr a)) (cadr (cdr a)) elev) ext))))))
  (strcat "{\"pts\":[" out "],\"closed\":" (itoa (logand 1 (cdr (assoc 70 d)))) ",\"layer\":\"" (j-str (cdr (assoc 8 d))) "\"}"))
(defun dump-dim (e d / v) (setq v (cdr (assoc 42 d)))
  (strcat "{\"value\":" (j-num v) ",\"text\":\"" (j-str (cdr (assoc 1 d))) "\",\"def1\":" (j-pt (cdr (assoc 10 d))) ",\"textpos\":" (j-pt (cdr (assoc 11 d))) ",\"def2\":" (j-pt (if (assoc 14 d) (cdr (assoc 14 d)) (cdr (assoc 13 d)))) ",\"layer\":\"" (j-str (cdr (assoc 8 d))) "\"}"))
(defun dump-mleader (e d / txt tip land dl dir th tpos sect stack out v)
  ;; nested sections: CONTEXT_DATA{ (10 text pos, 41 text height, 304 text) > LEADER{ (10 landing, 11 dir, 40 dogleg) > LEADER_LINE{ (10 tip)
  ;; closers: 303 "}" closes LEADER_LINE, 301 "}" closes LEADER / CONTEXT_DATA (stack)
  (setq sect "" stack '() tip '(0 0 0) land '(0 0 0) tpos '(0 0 0) dl 0.0 dir '(1 0 0) th 0.0 txt "")
  (foreach a d (setq v (cdr a))
    (cond ((and (member (car a) '(300 302 304)) (= (type v) 'STR) (wcmatch v "*{")) (setq stack (cons v stack) sect v))
          ((and (member (car a) '(301 303)) (= (type v) 'STR) (= v "}")) (setq stack (cdr stack) sect (if stack (car stack) "")))
          ((and (= (car a) 304) (= sect "CONTEXT_DATA{")) (setq txt v))
          ((and (= (car a) 10) (= sect "CONTEXT_DATA{")) (setq tpos v))
          ((and (= (car a) 41) (= sect "CONTEXT_DATA{") (= th 0.0)) (setq th v))
          ((and (= (car a) 10) (= sect "LEADER{")) (setq land v))
          ((and (= (car a) 11) (= sect "LEADER{")) (setq dir v))
          ((and (= (car a) 40) (= sect "LEADER{")) (setq dl v))
          ((and (= (car a) 10) (= sect "LEADER_LINE{") (equal tip '(0 0 0))) (setq tip v))))
  (strcat "{\"handle\":\"" (cdr (assoc 5 d)) "\",\"text\":\"" (j-str txt) "\",\"tip\":" (j-pt tip) ",\"landing\":" (j-pt land) ",\"textpos\":" (j-pt tpos) ",\"dogleg\":" (j-num dl) ",\"dir\":" (j-pt dir) ",\"th\":" (j-num th) ",\"layer\":\"" (j-str (cdr (assoc 8 d))) "\"}"))
(defun ss-each (ss fn / i) (if ss (progn (setq i 0) (while (< i (sslength ss)) (fn (ssname ss i)) (setq i (1+ i))))))
(defun dump-all (path / f e d typ lines plines dims mls first ss)
  (setq f (open path "w"))
  (write-line "{\"lines\":[" f) (setq first T)
  (ss-each (ssget "_X" '((0 . "LINE") (410 . "Model"))) (lambda (e) (write-line (strcat (if first "" ",") (dump-line e (entget e))) f) (setq first nil)))
  (write-line "],\"polylines\":[" f) (setq first T)
  (ss-each (ssget "_X" '((0 . "LWPOLYLINE") (410 . "Model"))) (lambda (e) (write-line (strcat (if first "" ",") (dump-pline e (entget e))) f) (setq first nil)))
  (write-line "],\"dims\":[" f) (setq first T)
  (ss-each (ssget "_X" '((0 . "DIMENSION") (410 . "Model"))) (lambda (e) (write-line (strcat (if first "" ",") (dump-dim e (entget e))) f) (setq first nil)))
  (write-line "],\"leaders\":[" f) (setq first T)
  (ss-each (ssget "_X" '((0 . "MULTILEADER") (410 . "Model"))) (lambda (e) (write-line (strcat (if first "" ",") (dump-mleader e (entget e))) f) (setq first nil)))
  (write-line "],\"layouts\":[" f) (setq first T)
  (setq ldict (cdr (assoc -1 (dictsearch (namedobjdict) "ACAD_LAYOUT"))) lnames '())
  (foreach a (entget ldict) (if (= (car a) 3) (setq lnames (append lnames (list (cdr a))))))
  (foreach ln lnames (if (/= ln "Model") (progn
    (setq lo (dictsearch ldict ln))
    (write-line (strcat (if first "" ",") "{\"name\":\"" (j-str ln) "\",\"paper\":[" (j-num (cdr (assoc 44 lo))) "," (j-num (cdr (assoc 45 lo))) "],\"units\":" (itoa (cdr (assoc 72 lo))) ",\"viewports\":[") f)
    (setq f1 T)
    (ss-each (ssget "_X" (list '(0 . "VIEWPORT") (cons 410 ln))) (lambda (e / d c w h) (setq d (entget e))
      (if (/= (cdr (assoc 69 d)) 1)
        (progn (setq c (cdr (assoc 10 d)) w (cdr (assoc 40 d)) h (cdr (assoc 41 d)))
          (write-line (strcat (if f1 "" ",") "[" (j-num (- (car c) (/ w 2))) "," (j-num (- (cadr c) (/ h 2))) "," (j-num (+ (car c) (/ w 2))) "," (j-num (+ (cadr c) (/ h 2))) "]") f) (setq f1 nil)))))
    (write-line "],\"frames\":[" f) (setq f1 T)
    (ss-each (ssget "_X" (list '(0 . "LWPOLYLINE") (cons 410 ln) '(90 . 4))) (lambda (e / d xs ys) (setq d (entget e))
      (if (= (logand 1 (cdr (assoc 70 d))) 1)
        (progn (setq xs '() ys '()) (foreach a d (if (= (car a) 10) (setq xs (cons (car (cdr a)) xs) ys (cons (cadr (cdr a)) ys))))
          (write-line (strcat (if f1 "" ",") "[" (j-num (apply 'min xs)) "," (j-num (apply 'min ys)) "," (j-num (apply 'max xs)) "," (j-num (apply 'max ys)) "]") f) (setq f1 nil)))))
    (write-line "]}" f) (setq first nil))))
  (write-line "]}" f) (close f) (princ "\nDUMP_OK"))
'''


def read(dwg, timeout=120):
    w = tempfile.mkdtemp(prefix="rd_"); lsp = os.path.join(w, "dump.lsp"); out = os.path.join(w, "dump.json")
    open(lsp, "w", encoding="ascii", errors="replace").write(LISP)
    t0 = time.time()
    ok, log, why = C.run(dwg, ["FILEDIA", "0", "CMDECHO", "0", f'(load "{lsp.replace(chr(92), "/")}")', f'(dump-all "{out.replace(chr(92), "/")}")'], timeout=timeout, workdir=w)
    if "DUMP_OK" not in log or not os.path.exists(out):
        raise RuntimeError("AutoCAD dump failed: " + "\n".join([l for l in log.splitlines() if l.strip()][-8:]))
    data = json.load(open(out, encoding="utf-8", errors="replace"))
    data["_source"] = os.path.abspath(dwg); data["_reader"] = "AutoCAD accoreconsole (entget)"; data["_seconds"] = round(time.time() - t0, 1)
    return data


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument("dwg"); ap.add_argument("--out"); a = ap.parse_args()
    d = read(a.dwg)
    print(f"AutoCAD read in {d['_seconds']}s: lines {len(d['lines'])}, polylines {len(d['polylines'])}, dims {len(d['dims'])}, leaders {len(d['leaders'])}, layouts {[l['name'] for l in d['layouts']]}")
    for l in d["layouts"]:
        print(f"  layout {l['name']}: paper {l['paper']} units {l['units']} viewports {len(l['viewports'])} frames {l['frames']}")
    for m in d["leaders"][:6]:
        print("  leader", m["text"][:24], "tip", m["tip"], "landing", m["landing"], "dogleg", m["dogleg"], "th", m["th"], "dir", m["dir"])
    if a.out:
        json.dump(d, open(a.out, "w"), indent=1)
