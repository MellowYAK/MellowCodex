from hub.output_checks import missing_document_outputs

def test_observation_and_success_prose_cannot_replace_requested_pdf(tmp_path):
 assert missing_document_outputs('Save the article as PDF',[{'tool':'browser_observe','result':{'text':'Saved successfully'}}],tmp_path)==['pdf']

def test_corrupt_file_is_not_accepted_and_read_request_needs_no_output(tmp_path):
 path=tmp_path/'wrong.pdf';path.write_text('not a PDF')
 actions=[{'tool':'browser_save_pdf','result':{'path':str(path),'verified_pdf':True}}]
 assert missing_document_outputs('Create a PDF',actions,tmp_path)==['pdf']
 assert missing_document_outputs('Read the PDF',[],tmp_path)==[]

def test_actual_generated_document_is_required(tmp_path):
 import pymupdf
 path=tmp_path/'output.pdf'
 with pymupdf.open() as doc:
  doc.new_page().insert_text((40,40),'Document output');doc.save(path)
 assert missing_document_outputs('Save as PDF',[{'tool':'browser_save_pdf','result':{'path':str(path)}}],tmp_path)==[]
