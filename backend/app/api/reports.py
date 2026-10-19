"""
Reports API Router
T1.12: Relatório PDF (Jinja2 + WeasyPrint, upload a Storage, GET /reports/{id})
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import io

from app.services.reports_service import ReportsService
from app.auth import get_current_user

# Create router
router = APIRouter(prefix="/reports", tags=["reports"])

# Initialize service
reports_service = ReportsService()


class StructuralReportRequest(BaseModel):
    """Request model for generating a structural analysis report."""
    beam_data: dict
    analysis_results: dict
    user_id: Optional[str] = None


@router.post("/structural", status_code=status.HTTP_201_CREATED)
async def generate_structural_report(
    request: StructuralReportRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Generate a PDF report for structural beam analysis.

    Args:
        request: StructuralReportRequest containing beam data and analysis results
        current_user: Current authenticated user

    Returns:
        dict: Report ID for retrieving the generated PDF
    """
    try:
        # Use authenticated user's ID if not provided in request
        user_id = request.user_id or current_user.get("sub")

        # Generate the report
        report_id = await reports_service.generate_structural_report(
            beam_data=request.beam_data,
            analysis_results=request.analysis_results,
            user_id=user_id
        )

        return {
            "report_id": report_id,
            "message": "Report generated successfully",
            "download_url": f"/reports/{report_id}"
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate report: {str(e)}"
        )


@router.get("/{report_id}")
async def get_report(report_id: str):
    """
    Retrieve a PDF report by ID.

    Args:
        report_id: The report ID (UUID)

    Returns:
        StreamingResponse: PDF file content
    """
    try:
        # Get the PDF bytes from storage
        pdf_bytes = await reports_service.get_report(report_id)

        # Return as streaming response
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"inline; filename=report_{report_id}.pdf"
            }
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND if "not found" in str(e).lower() else status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve report: {str(e)}"
        )


@router.delete("/{report_id}", status_code=status.HTTP_200_OK)
async def delete_report(
    report_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a report by ID.

    Args:
        report_id: The report ID (UUID)
        current_user: Current authenticated user

    Returns:
        dict: Confirmation message
    """
    try:
        # Delete the report
        success = await reports_service.delete_report(report_id)

        if success:
            return {
                "message": f"Report {report_id} deleted successfully"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete report"
            )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete report: {str(e)}"
        )