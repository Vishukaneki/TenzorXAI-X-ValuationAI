"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";

export type ValuationFormData = {
  locality: string;
  property_type: string;
  subtype: string;
  size_sqft: number;
  age_years: number;
  floor_num?: number;
  total_floors?: number;
  has_lift?: boolean;
  legal_status?: string;
  occupancy_status?: string;
  rental_yield?: number;
};

type InputFormProps = {
  onSubmit: (data: ValuationFormData | FormData) => void;
  loading: boolean;
  error?: string;
};

const localityOptions = [
  "Kondapur",
  "Gachibowli",
  "Jubilee Hills",
  "Koramangala",
  "Whitefield",
  "HSR Layout",
  "South Delhi",
  "Dwarka",
  "Bandra West",
  "Powai",
];

const propertyTypeOptions = [
  { value: "apartment", label: "Apartment" },
  { value: "villa", label: "Villa / House" },
  { value: "plot", label: "Plot" },
  { value: "commercial", label: "Commercial" },
];

const subtypeByType: Record<string, string[]> = {
  apartment: ["1BHK", "2BHK", "3BHK", "4BHK"],
  villa: ["independent_house", "row_house", "villa"],
  plot: ["residential_plot", "corner_plot"],
  commercial: ["shop", "office"],
};

function readNumber(formData: FormData, key: string) {
  const value = formData.get(key);
  if (value === null || value === "") return undefined;
  return Number(value);
}

export default function InputForm({ onSubmit, loading, error }: InputFormProps) {
  const [propertyType, setPropertyType] = useState("apartment");
  const [subtype, setSubtype] = useState(subtypeByType.apartment[1]);
  const [locality, setLocality] = useState(localityOptions[0]);
  const [image, setImage] = useState<File | null>(null);
  const didMount = useRef(false);

  useEffect(() => {
    if (didMount.current) {
      setSubtype(subtypeByType[propertyType][0]);
      return;
    }

    didMount.current = true;
  }, [propertyType]);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);

    // If an image is selected, submit as multipart form data
    if (image) {
      const multipartData = new FormData();
      multipartData.append("locality", locality);
      multipartData.append("property_type", propertyType);
      multipartData.append("subtype", subtype);
      multipartData.append("size_sqft", formData.get("size_sqft") as string);
      multipartData.append("age_years", formData.get("age_years") as string);
      
      const floorNum = readNumber(formData, "floor_num");
      if (floorNum !== undefined) {
        multipartData.append("floor_num", floorNum.toString());
      }
      
      const totalFloors = readNumber(formData, "total_floors");
      if (totalFloors !== undefined) {
        multipartData.append("total_floors", totalFloors.toString());
      }
      
      multipartData.append("has_lift", formData.get("has_lift") as string);
      multipartData.append("legal_status", formData.get("legal_status") as string);
      multipartData.append("occupancy_status", formData.get("occupancy_status") as string);
      
      const rentalYield = readNumber(formData, "rental_yield");
      if (rentalYield !== undefined) {
        multipartData.append("rental_yield", rentalYield.toString());
      }
      
      multipartData.append("image", image);
      onSubmit(multipartData);
    } else {
      // Submit as JSON if no image
      onSubmit({
        locality,
        property_type: propertyType,
        subtype,
        size_sqft: Number(formData.get("size_sqft")),
        age_years: Number(formData.get("age_years")),
        floor_num: readNumber(formData, "floor_num"),
        total_floors: readNumber(formData, "total_floors"),
        has_lift: formData.get("has_lift") === "true",
        legal_status: String(formData.get("legal_status") || "clear"),
        occupancy_status: String(formData.get("occupancy_status") || "self_occupied"),
        rental_yield: readNumber(formData, "rental_yield"),
      });
    }
  }

  return (
    <section className="panel sticky">
      <p className="section-label">Collateral Input</p>
      <h2>Property file</h2>
      <form className="form-grid" onSubmit={handleSubmit}>
        <div className="field">
          <label htmlFor="locality">Locality</label>
          <select id="locality" name="locality" value={locality} onChange={(event) => setLocality(event.target.value)}>
            {localityOptions.map((locality) => (
              <option value={locality} key={locality}>
                {locality}
              </option>
            ))}
          </select>
          <p className="field-hint">Use the nearest market instead of free-typing a locality.</p>
        </div>

        <div className="two-col">
          <div className="field">
            <label htmlFor="property_type">Asset type</label>
            <select id="property_type" name="property_type" value={propertyType} onChange={(event) => setPropertyType(event.target.value)}>
              {propertyTypeOptions.map((option) => (
                <option value={option.value} key={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="subtype">Subtype</label>
            <select id="subtype" name="subtype" value={subtype} onChange={(event) => setSubtype(event.target.value)}>
              {subtypeByType[propertyType].map((subtypeOption) => (
                <option value={subtypeOption} key={subtypeOption}>
                  {subtypeOption.replaceAll("_", " ")}
                </option>
              ))}
            </select>
            <p className="field-hint">Subtype options update when the asset type changes.</p>
          </div>
        </div>

        <div className="two-col">
          <div className="field">
            <label htmlFor="size_sqft">Size, sqft</label>
            <input id="size_sqft" name="size_sqft" type="number" min="100" defaultValue="1150" required />
          </div>
          <div className="field">
            <label htmlFor="age_years">Age, years</label>
            <input id="age_years" name="age_years" type="number" min="0" defaultValue="8" required />
          </div>
        </div>

        <div className="two-col">
          <div className="field">
            <label htmlFor="floor_num">Floor</label>
            <input id="floor_num" name="floor_num" type="number" min="0" defaultValue="5" />
          </div>
          <div className="field">
            <label htmlFor="total_floors">Total floors</label>
            <input id="total_floors" name="total_floors" type="number" min="1" defaultValue="12" />
          </div>
        </div>

        <div className="two-col">
          <div className="field">
            <label htmlFor="has_lift">Lift</label>
            <select id="has_lift" name="has_lift" defaultValue="true">
              <option value="true">Available</option>
              <option value="false">Not available</option>
            </select>
          </div>
          <div className="field">
            <label htmlFor="legal_status">Legal status</label>
            <select id="legal_status" name="legal_status" defaultValue="clear">
              <option value="clear">Clear</option>
              <option value="pending">Pending</option>
              <option value="disputed">Disputed</option>
            </select>
          </div>
        </div>

        <div className="two-col">
          <div className="field">
            <label htmlFor="occupancy_status">Occupancy</label>
            <select id="occupancy_status" name="occupancy_status" defaultValue="self_occupied">
              <option value="self_occupied">Self occupied</option>
              <option value="rented">Rented</option>
              <option value="vacant">Vacant</option>
            </select>
          </div>
          <div className="field">
            <label htmlFor="rental_yield">Rental yield %</label>
            <input id="rental_yield" name="rental_yield" type="number" step="0.1" min="0" defaultValue="3.2" />
          </div>
        </div>
        <div className="field">
          <label htmlFor="property_image">Property Image (optional)</label>
          <input 
            id="property_image" 
            name="property_image" 
            type="file" 
            accept="image/*" 
            onChange={(e) => setImage(e.target.files?.[0] || null)} 
          />
          <p className="field-hint">Upload an image of the property for condition analysis (optional)</p>
        </div>
        <button className="submit-button" disabled={loading} type="submit">
          {loading ? "Running credit model..." : "Run valuation"}
        </button>
      </form>
      {error ? <div className="error-box">{error}</div> : null}
    </section>
  );
}
