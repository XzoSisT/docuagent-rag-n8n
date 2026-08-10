# ชุดเอกสาร PDF สำหรับทดสอบ DocuAgent RAG

ดาวน์โหลดและตรวจสอบเมื่อวันที่ 10 สิงหาคม 2026 โดยเลือกเฉพาะไฟล์จากเว็บไซต์ของเจ้าของเอกสารโดยตรง ไฟล์ PDF ถูกเก็บไว้ในโฟลเดอร์นี้สำหรับทดสอบภายในเครื่อง แต่ถูกตั้งค่าไม่ให้นำขึ้น Git เพื่อลดขนาด repository และหลีกเลี่ยงการเผยแพร่ไฟล์ของบุคคลอื่นซ้ำ ส่วนไฟล์ `SOURCES.md` นี้สามารถนำขึ้น Git เพื่อบันทึกที่มาและวิธีสร้างชุดทดสอบซ้ำได้

## 1. `nist-ai-rmf-1.0.pdf`

- ชื่อเอกสาร: Artificial Intelligence Risk Management Framework (AI RMF 1.0)
- เจ้าของเอกสาร: National Institute of Standards and Technology (NIST), U.S. Department of Commerce
- หน้าข้อมูลอย่างเป็นทางการ: <https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-ai-rmf-10>
- URL ของ PDF: <https://nvlpubs.nist.gov/nistpubs/ai/nist.ai.100-1.pdf>
- เหตุผลที่เลือก: เป็นเอกสารมาตรฐานจากหน่วยงานรัฐที่เชื่อถือได้ มีหัวข้อ ลำดับเลข ตาราง รูปภาพ และเลขหน้าชัดเจน เหมาะใช้เป็น baseline ภาษาอังกฤษเพื่อทดสอบ extraction, chunking, retrieval และการอ้างอิงเลขหน้า
- ผลตรวจ: 48 หน้า, ดึงข้อความได้ 48 หน้า, รวมประมาณ 106,446 ตัวอักษร, ไม่เข้ารหัส
- SHA-256: `7576EDB531D9848825814EE88E28B1795D3A84B435B4B797D3670EAFDC4A89F1`
- คำถามทดลอง: `What are the four core functions of the NIST AI RMF?`

## 2. `rag-original-paper.pdf`

- ชื่อเอกสาร: Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks
- เจ้าของผลงาน: Patrick Lewis และคณะ
- หน้าบทความ: <https://arxiv.org/abs/2005.11401>
- URL ของ PDF: <https://arxiv.org/pdf/2005.11401>
- เหตุผลที่เลือก: เป็นงานวิจัยต้นฉบับของแนวคิด RAG และตรงกับหัวข้อโปรเจกต์มากที่สุด รูปแบบสองคอลัมน์ ตาราง รูป และรายการอ้างอิงช่วยทดสอบลำดับข้อความและความแม่นยำของ retrieval ในเอกสารวิชาการ
- ผลตรวจ: 19 หน้า, ดึงข้อความได้ 19 หน้า, รวมประมาณ 69,058 ตัวอักษร, ไม่เข้ารหัส
- SHA-256: `23E3249E9A1E75418D82EFECAB0EA8C4D033B89C93742F63208D47CE01F21233`
- คำถามทดลอง: `How do RAG-Sequence and RAG-Token differ?`

## 3. `etda-ai-governance-business-th.pdf`

- ชื่อเอกสาร: ธรรมาภิบาลการใช้ปัญญาประดิษฐ์ในภาคธุรกิจ
- เจ้าของเอกสาร: AI Governance Center by ETDA
- URL ของ PDF: <https://www.etda.or.th/getattachment/Our-Service/AIGC/Research-and-Recommendation/08-AIGovernanceInBusiness-Pinnaree.pdf.aspx?lang=th-TH>
- เหตุผลที่เลือก: เป็นเอกสารภาษาไทยจากหน่วยงานภาครัฐ มีคำไทยปนศัพท์อังกฤษ เช่น AI Governance และ Human-in-the-loop จึงเหมาะทดสอบ embedding ภาษาไทย การแบ่งข้อความ และการค้นคืนแบบข้ามภาษา
- ผลตรวจ: 7 หน้า, ดึงข้อความได้ 5 หน้า, รวมประมาณ 8,743 ตัวอักษร, ไม่เข้ารหัส หน้าที่ 1 และ 7 เป็นหน้ากราฟิกจึงไม่มีข้อความให้ `pypdf` ดึงออกมา ซึ่งเป็นกรณีขอบเขตที่มีประโยชน์สำหรับทดสอบระบบจริง
- SHA-256: `B423D2E5BD0606FCA4FEFA5E06741091679155905BE92031F820510FA32B0E0B`
- คำถามทดลอง: `องค์กรควรจัดโครงสร้างการบริหารภายในเพื่อกำกับดูแล AI อย่างไร?`

## ลำดับการทดสอบที่แนะนำ

1. เริ่มจาก NIST เพื่อยืนยันว่า pipeline ภาษาอังกฤษทำงานครบ
2. ใช้งานวิจัย RAG เพื่อตรวจเอกสารสองคอลัมน์และคำศัพท์เฉพาะทาง
3. ใช้ ETDA เพื่อตรวจภาษาไทยและการจัดการหน้าที่ไม่มีข้อความ

หากต้องการนำเอกสารเหล่านี้ไปเผยแพร่พร้อม repository ควรตรวจเงื่อนไขการใช้งานของเจ้าของเอกสารก่อน โดยค่าเริ่มต้นให้ repository เก็บเฉพาะรายการ URL และดาวน์โหลดเอกสารจากต้นทางสำหรับการทดสอบภายในเครื่อง
