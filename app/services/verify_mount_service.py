from sqlmodel import Session
from app.models.verify_mount import VerifyMount
from uuid import UUID


class VerifyMountService:
    def __init__(self, session: Session):
        self.session = session

    def get_mount(self, user_id: UUID):
        verify_mount = self.session.query(VerifyMount).filter(
            VerifyMount.user_id == user_id).first()
        if not verify_mount:
            return {"mount": 0}
        return {"mount": verify_mount.mount}

    def update_mount(self, user_id: UUID, new_mount: int):
        verify_mount = self.session.query(VerifyMount).filter(
            VerifyMount.user_id == user_id).first()
        if not verify_mount:
            verify_mount = VerifyMount(user_id=user_id, mount=new_mount)
            self.session.add(verify_mount)
        else:
            verify_mount.mount = new_mount
            self.session.add(verify_mount)
        self.session.commit()
        return {"mount": verify_mount.mount}
