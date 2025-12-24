## DrugGenix Backend

### Run

Python requirement: 3.12

From `drug-backend/`:

```bash
python -m uvicorn main:app --reload --port 8000
```

API base:

```
http://localhost:8000/api/v1
```

Swagger:

```
http://localhost:8000/docs
```

### Smoke test (manual)

Most endpoints require auth with `Authorization: Bearer <JWT>`.

Auth endpoints:

- `POST /api/v1/auth/signup`
- `POST /api/v1/auth/login` (JSON)
- `POST /api/v1/auth/token` (OAuth2 form)

#### PowerShell (Windows)

1) Sign up

```powershell
$signupBody = @{ email = "demo@example.com"; password = "demo123" } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/api/v1/auth/signup" -ContentType "application/json" -Body $signupBody
```

2) Login + capture token

```powershell
$loginBody = @{ email = "demo@example.com"; password = "demo123" } | ConvertTo-Json
$token = (Invoke-RestMethod -Method Post -Uri "http://localhost:8000/api/v1/auth/login" -ContentType "application/json" -Body $loginBody).access_token
"TOKEN=$token"
```

3) Upload a protein (PDB/CIF)

If you have `curl.exe` available:

```powershell
curl.exe -s -X POST "http://localhost:8000/api/v1/proteins/upload" `
  -H "Authorization: Bearer $token" `
  -F "file=@PATH_TO_YOUR_PROTEIN.pdb"
```

4) List proteins (to get `protein_id`)

```powershell
Invoke-RestMethod -Method Get -Uri "http://localhost:8000/api/v1/proteins" -Headers @{ Authorization = "Bearer $token" }
```

5) Detect pockets

```powershell
Invoke-RestMethod -Method Get -Uri "http://localhost:8000/api/v1/proteins/PROTEIN_ID/pockets" -Headers @{ Authorization = "Bearer $token" }
```

6) Generate molecules (blind)

```powershell
$genBody = @{ num = 5 } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/api/v1/molecules/generate" -Headers @{ Authorization = "Bearer $token" } -ContentType "application/json" -Body $genBody
```

7) Generate molecules (target-aware)

`protein_id` is the preferred field (legacy `target_id` is still accepted).

```powershell
$genTargetBody = @{ protein_id = PROTEIN_ID; pocket_idx = 0; num = 8 } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/api/v1/molecules/generate" -Headers @{ Authorization = "Bearer $token" } -ContentType "application/json" -Body $genTargetBody
```

Notes:

- If you omit `pocket_idx`, pocket index `0` is selected.
- When `protein_id` is provided, the server auto-detects pockets and extracts Level-1 pocket features (volume, hydrophobicity/charge/H-bond heuristics) to condition generation.
