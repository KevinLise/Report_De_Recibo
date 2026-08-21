export function Atmosphere() {
  return (
    <div className="atmosphere" aria-hidden="true">
      <video
        className="atmosphere__media"
        autoPlay
        muted
        loop
        playsInline
        poster="/bg.jpg"
      >
        <source src="/bg.mp4" type="video/mp4" />
      </video>
      <div className="atmosphere__blur" />
      <div className="atmosphere__dots" />
    </div>
  );
}
