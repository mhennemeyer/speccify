require File.dirname(__FILE__) + "/../test_helper.rb"

describe "Example name " do
  it "@==ß?¿ asd" do
    1.should be(1)
  end
  
  it "asd @==ß?¿" do
    1.should be(1)
  end
end