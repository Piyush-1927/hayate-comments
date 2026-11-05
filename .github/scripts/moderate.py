import json, os, re, unicodedata, urllib.request

ev = json.load(open(os.environ["GITHUB_EVENT_PATH"]))
LEET = str.maketrans({"@": "a", "4": "a", "3": "e", "1": "i", "!": "i", "|": "i",
                      "0": "o", "5": "s", "$": "s", "7": "t"})

def norm(t):
    t = unicodedata.normalize("NFKD", str(t).lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return t.translate(LEET)

def sq(w):
    return re.sub(r"(.)\1+", r"\1", w)

BAD = set()
for line in open("blocked-words.txt", encoding="utf-8"):
    w = line.strip()
    if w and not w.startswith("#"):
        BAD.add(sq(norm(w)))

FW = {sq(x) for x in ["fuck", "fucking", "fucked", "fucker", "fuckers", "fucks", "fck", "fuk", "fuckin", "fukin"]}
TG = {sq(x) for x in ["you", "u", "ya", "yo", "ur", "your", "yourself", "off", "him", "her", "them", "everyone"]}

def directed(text):
    w = norm(text).split()
    for i in range(len(w) - 1):
        if re.search(r"[,.;:?\-]$", w[i]):
            continue
        c = sq(re.sub(r"[^a-z]", "", w[i]))
        n = sq(re.sub(r"[^a-z]", "", w[i + 1]))
        if c in FW and n in TG:
            return True
    return False

def hit(w):
    c = sq(w)
    return c in BAD or re.sub(r"(ing|ers?|ed|es|s|y)$", "", c) in BAD

def bad(text):
    toks = [x for x in re.split(r"[^a-z]+", norm(text)) if x]
    out, run = [], ""
    for w in toks:
        if len(w) == 1:
            run += w
            continue
        if len(run) > 1:
            out.append(run)
        run = ""
        out.append(w)
    if len(run) > 1:
        out.append(run)
    return any(hit(w) for w in out)

def gql(query, var):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": {"id": var}}).encode(),
        headers={"Authorization": "bearer " + os.environ["GITHUB_TOKEN"],
                 "Content-Type": "application/json"})
    print(urllib.request.urlopen(req).read().decode())

if "comment" in ev:
    obj, text = ev["comment"], ev["comment"].get("body", "")
    q = "mutation($id:ID!){deleteDiscussionComment(input:{id:$id}){clientMutationId}}"
else:
    obj = ev["discussion"]
    text = (obj.get("title") or "") + " " + (obj.get("body") or "")
    q = "mutation($id:ID!){deleteDiscussion(input:{id:$id}){clientMutationId}}"

user = obj.get("user") or {}
if user.get("type") == "Bot" or obj.get("author_association") in ("OWNER", "MEMBER", "COLLABORATOR"):
    print("skipped (trusted author)")
elif bad(text) or directed(text):
    print("deleting", obj.get("node_id"))
    gql(q, obj["node_id"])
else:
    print("clean")
