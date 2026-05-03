"use client";

import { ValuationResponse } from "@/app/page";

export default function ImageAnalysisPanel({ result }: { result: ValuationResponse }) {
  // Check if image analysis data exists
  const imageAnalysis = result.image_analysis;
  
  if (!imageAnalysis) {
    return null;
  }

  return (
    <section className="result-card">
      <div className="card-topline">
        <div>
          <p className="section-label">Image Analysis</p>
          <h2>Visual Property Assessment</h2>
          <p className="field-hint">AI-powered analysis of property condition from uploaded image</p>
        </div>
        <span className="pill pill-blue">
          {imageAnalysis.confidence_in_analysis ? 
            `${Math.round(imageAnalysis.confidence_in_analysis * 100)}% confidence` : 
            'Analysis complete'}
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6">
        <div className="space-y-4">
          <h3 className="font-semibold text-lg">Condition Assessment</h3>
          
          <div className="space-y-3">
            <div>
              <p className="text-sm text-muted">Construction Quality</p>
              <p className="font-medium capitalize">{imageAnalysis.construction_quality || 'Not detected'}</p>
            </div>
            
            <div>
              <p className="text-sm text-muted">Visible Condition</p>
              <p className="font-medium capitalize">{imageAnalysis.visible_condition || 'Not detected'}</p>
            </div>
            
            <div>
              <p className="text-sm text-muted">Property Type Match</p>
              <p className="font-medium">
                {imageAnalysis.property_type_matches_claimed === true ? '✅ Matches' : 
                 imageAnalysis.property_type_matches_claimed === false ? '❌ Mismatch' : 
                 'Unknown'}
              </p>
            </div>
          </div>
        </div>

        <div className="space-y-4">
          <h3 className="font-semibold text-lg">Detected Issues</h3>
          
          {imageAnalysis.visible_issues && imageAnalysis.visible_issues.length > 0 ? (
            <ul className="space-y-2">
              {imageAnalysis.visible_issues.map((issue: string, index: number) => (
                <li key={index} className="flex items-center">
                  <span className="mr-2">⚠️</span>
                  <span className="capitalize">{issue.replace('_', ' ')}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-muted">No significant issues detected</p>
          )}
        </div>
      </div>

      {result.confidence_breakdown?.image_quality && (
        <div className="mt-6 pt-4 border-t border-line">
          <p className="text-sm text-muted">
            Image quality score contributed {Math.round(result.confidence_breakdown.image_quality * 100)}% 
            to the overall confidence score
          </p>
        </div>
      )}
    </section>
  );
}