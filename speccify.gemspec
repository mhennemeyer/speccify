spec = Gem::Specification.new do |spec| 
  spec.name = 'speccify' 
  spec.summary = 'Speccify is a lightweight alternative to RSpec.' 
  spec.description = "Speccify is a lightweight alternative to RSpec."
  spec.author = 'Matthias Hennemeyer' 
  spec.email = 'mhennemeyer@gmail.com' 
  spec.homepage = 'http://github.com/mhennemeyer/speccify' 
  spec.files = ["README.markdown", "lib/speccify.rb"] 
  spec.version = '0.1.2'
  spec.add_dependency("minitest", ["> 1.3.0"])
end