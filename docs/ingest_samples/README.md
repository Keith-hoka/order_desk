# Phase 6 — ingest samples (before / after standardization)

Representative packed emails and what the standardization layer turns them
into. The `.eml` files are RFC 822 messages wrapping the human slice with
realistic noise; the standardized body is what the pipeline actually sees.

## What standardization strips vs keeps

The layer removes **machine noise** that would pollute extraction: RFC 3676
signature blocks (the `-- ` delimiter and the legal boilerplate below it),
quoted reply history (`On ... wrote:` and `>` lines), HTML markup, and
client footers (`Sent from my iPhone`). It deliberately **keeps** the human
sign-off (`Kind regards, Dana`) -- that is body text, not noise, and the
buyer name is often there for extraction to use. The faithful sample below
shows a polite sign-off preserved; the signature sample shows a legal
footer stripped while the sign-off stays.

## faithful

Source: [`faithful.eml`](faithful.eml)

**Raw `.eml` (excerpt):**
```
Subject: Packing tape reorder - PO-73218
From: dana.whitfield@harbourline.com.au
To: orders@meridianpackaging.example
Date:
Message-ID: <HUM-0001@harbourline.example>
Content-Type: text/plain; charset="utf-8"
Content-Transfer-Encoding: quoted-printable
MIME-Version: 1.0

Good morning,

We would like to reorder 72 rolls of clear packing tape for our Botany wareho=
use. Please book this against PO-73218 and confirm a delivery date at your co=
nvenience.

Kind regards,
Dana Whitfield
Harbourline Logistics Pty Ltd
```

**Standardized body (what the pipeline sees):**
```
Good morning,

We would like to reorder 72 rolls of clear packing tape for our Botany warehouse. Please book this against PO-73218 and confirm a delivery date at your convenience.

Kind regards,
Dana Whitfield
Harbourline Logistics Pty Ltd
```

## signature

Source: [`signature.eml`](signature.eml)

**Raw `.eml` (excerpt):**
```
Subject: Edge protectors order
From: marcus.yeo@redgumfurniture.com.au
To: orders@meridianpackaging.example
Date:
Message-ID: <HUM-0023@harbourline.example>
Content-Type: text/plain; charset="utf-8"
Content-Transfer-Encoding: 7bit
MIME-Version: 1.0

Send 10 bundles of edge protectors.
PO 4500483610.
Regards
Marcus Yeo


-- 
Dana
HarbourLine
This email and any attachments are confidential.
```

**Standardized body (what the pipeline sees):**
```
Send 10 bundles of edge protectors.
PO 4500483610.
Regards
Marcus Yeo
```

## html

Source: [`html.eml`](html.eml)

**Raw `.eml` (excerpt):**
```
Subject: bubble wrap
From: sofia@bightandbay.com.au
To: orders@meridianpackaging.example
Date:
Message-ID: <HUM-0004@harbourline.example>
Content-Type: text/html; charset="utf-8"
Content-Transfer-Encoding: 7bit
MIME-Version: 1.0

<html><body><p>6 rolls bubble wrap to port adelaide pls
Thanks
</p></body></html>
```

**Standardized body (what the pipeline sees):**
```
6 rolls bubble wrap to port adelaide pls Thanks
```

## reply

Source: [`reply.eml`](reply.eml)

**Raw `.eml` (excerpt):**
```
Subject: Re: Packing tape reorder - PO-73218
From: dana.whitfield@harbourline.com.au
To: orders@meridianpackaging.example
Date:
Message-ID: <HUM-0001@harbourline.example>
In-Reply-To: <q-prior@x.com>
References: <q-prior@x.com>
Content-Type: text/plain; charset="utf-8"
Content-Transfer-Encoding: 7bit
MIME-Version: 1.0

72 rolls please, same as last time.

On Mon, 5 May 2026, Sales wrote:
> How many rolls of packing tape did you need?
> Let us know.
```

**Standardized body (what the pipeline sees):**
```
72 rolls please, same as last time.
```

**Asks raised:** ['email is a reply; order details may be in the conversation history not included here -- review against the thread']

**Threading:** is_reply=True, in_reply_to=<q-prior@x.com>
