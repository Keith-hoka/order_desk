export type ReviewStatus = "pending" | "approved" | "edited" | "rejected";

export interface FieldFlag {
  path: string;
  raw_confidence: number;
  calibrated_confidence: number;
  in_band: boolean;
}

export interface LineItem {
  product_text: string;
  quantity: number | null;
  unit_text: string | null;
  unit_price_text: string | null;
  item_notes: string | null;
}

export interface Extraction {
  customer_po_text: string | null;
  requested_date_text: string | null;
  delivery_address_text: string | null;
  buyer_name_text: string | null;
  notes: string | null;
  line_items: LineItem[];
}

export interface Fulfillment {
  submitted: boolean;
  order_id: string | null;
  reason: string;
  unresolved: string[];
}

export interface ReviewItem {
  id: string;
  subject: string;
  body: string;
  extraction: Extraction | null;
  field_flags: FieldFlag[];
  asks: string[];
  violations: string[];
  priority: number;
  status: ReviewStatus;
  edits: Record<string, string>;
  fulfillment?: Fulfillment | null;
}
